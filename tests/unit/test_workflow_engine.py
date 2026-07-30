"""Task 6.1 Workflow Engine tests."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.tools.types import ToolResult
from app.workflow.base import WorkflowRunStatus
from app.workflow.executor import WorkflowExecutor
from app.workflow.graph import WorkflowGraph
from app.workflow.node import WorkflowNode
from app.workflow.registry import WorkflowRegistry
from app.workflow.examples.software_team_workflow import (
    build_software_team_workflow,
)


class MockRuntime:
    def __init__(self, *, fail_agents: set[str] | None = None) -> None:

        self.calls: list[AgentTask] = []
        self._fail = fail_agents or set()

    def run(
        self,
        task: AgentTask,
        *,
        config=None,
        **kwargs: Any,
    ) -> AgentResult:

        self.calls.append(task)
        name = task.agent_name
        ok = name not in self._fail

        return AgentResult(
            success=ok,
            model="mock",
            content=f"output-from-{name}",
        )


class EchoToolExecutor:
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:

        if tool_name != "echo":

            return ToolResult(
                success=False,
                content=f"unknown tool {tool_name}",
            )

        return ToolResult(
            success=True,
            content=str(arguments.get("message", "")),
        )


def test_graph_detects_cycle() -> None:

    graph = WorkflowGraph(id="g1")
    graph.add_node(WorkflowNode.agent(node_id="a", agent_name="product"))
    graph.add_node(WorkflowNode.agent(node_id="b", agent_name="product"))
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")

    with pytest.raises(ValueError, match="cycle"):

        graph.validate()


def test_linear_agent_workflow_via_runtime() -> None:

    graph = WorkflowGraph(id="linear", entry_node_id="n1")
    graph.add_node(
        WorkflowNode.agent(node_id="n1", agent_name="product")
    )
    graph.add_node(
        WorkflowNode.agent(
            node_id="n2",
            agent_name="architecture",
            message_template="{node:n1:output}",
        )
    )
    graph.add_edge("n1", "n2")

    runtime = MockRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    result = executor.run(
        graph,
        session_id="s1",
        user_message="build system",
    )

    assert result.status == WorkflowRunStatus.COMPLETED
    assert len(runtime.calls) == 2
    assert runtime.calls[0].agent_name == "product"
    assert "output-from-product" in runtime.calls[1].user_message


def test_conditional_branch_skips_reviewer_path() -> None:

    graph = WorkflowGraph(id="cond", entry_node_id="dev")
    graph.add_node(
        WorkflowNode.agent(
            node_id="dev",
            agent_name="developer",
            on_failure="continue",
        )
    )
    graph.add_node(
        WorkflowNode.conditional(
            node_id="c",
            source_key="last_agent_success",
            equals=True,
        )
    )
    graph.add_node(
        WorkflowNode.agent(node_id="rev", agent_name="reviewer")
    )
    graph.add_node(
        WorkflowNode.tool(
            node_id="tail",
            tool_name="echo",
            arguments={"message": "done"},
        )
    )

    graph.add_edge("dev", "c")
    graph.add_edge("c", "rev", condition="true")
    graph.add_edge("c", "tail", condition="false")

    runtime = MockRuntime(fail_agents={"developer"})
    tools = EchoToolExecutor()
    executor = WorkflowExecutor(runtime=runtime, tool_executor=tools)

    result = executor.run(graph, session_id="s")

    assert result.status == WorkflowRunStatus.COMPLETED
    assert len(runtime.calls) == 1
    assert "done" in result.node_results["tail"].output


def test_human_approval_pause_and_resume() -> None:

    graph = WorkflowGraph(id="approve", entry_node_id="h")
    graph.add_node(
        WorkflowNode.human_approval(
            node_id="h",
            prompt="OK?",
        )
    )
    graph.add_node(
        WorkflowNode.tool(
            node_id="t",
            tool_name="echo",
            arguments={"message": "shipped"},
        )
    )
    graph.add_edge("h", "t")

    executor = WorkflowExecutor(
        runtime=MockRuntime(),
        tool_executor=EchoToolExecutor(),
    )

    first = executor.run(graph, session_id="s")

    assert first.status == WorkflowRunStatus.WAITING_APPROVAL
    assert first.pending_node_id == "h"

    second = executor.resume(
        first.run_id,
        approval_payload={"approved": True},
    )

    assert second.status == WorkflowRunStatus.COMPLETED
    assert second.node_results["t"].success


def test_agent_retry_on_failure() -> None:

    graph = WorkflowGraph(id="retry", entry_node_id="a")
    graph.add_node(
        WorkflowNode.agent(
            node_id="a",
            agent_name="product",
            max_retries=1,
        )
    )

    calls = {"n": 0}

    class FlakyRuntime:
        def run(self, task, *, config=None, **kwargs):
            calls["n"] += 1

            if calls["n"] == 1:

                return AgentResult(
                    success=False,
                    model="m",
                    content="fail",
                )

            return AgentResult(
                success=True,
                model="m",
                content="ok",
            )

    executor = WorkflowExecutor(runtime=FlakyRuntime())

    result = executor.run(graph, session_id="s")

    assert result.status == WorkflowRunStatus.COMPLETED
    assert calls["n"] == 2


def test_registry_and_example_workflow() -> None:

    graph = build_software_team_workflow()
    graph.validate()

    reg = WorkflowRegistry()
    reg.register(graph)

    assert reg.get("software_team_v1").name == "AI Software Team"
    assert len(reg.get("software_team_v1").nodes) >= 6
