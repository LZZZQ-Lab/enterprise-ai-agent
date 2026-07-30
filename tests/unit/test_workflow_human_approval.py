"""Human approval workflow tests (Task 6.3)."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.workflow.base import WorkflowRunStatus
from app.workflow.executor import WorkflowExecutor
from app.workflow.graph import WorkflowGraph
from app.workflow.human_node import ApprovalAction
from app.workflow.human_node import HumanApprovalNode
from app.workflow.node import WorkflowNode
from app.workflow.examples.team_human_approval_workflow import (
    build_team_human_approval_workflow,
)


class MockRuntime:
    def __init__(self) -> None:
        self.calls: list[AgentTask] = []

    def run(
        self,
        task: AgentTask,
        *,
        config=None,
        **kwargs: Any,
    ) -> AgentResult:
        self.calls.append(task)
        name = task.agent_name
        return AgentResult(
            success=True,
            model="mock",
            content=f"output-from-{name}",
        )


def test_human_node_reject_fails_workflow() -> None:
    graph = WorkflowGraph(id="reject", entry_node_id="h")
    graph.add_node(
        HumanApprovalNode(
            node_id="h",
            prompt="Approve?",
        ).to_workflow_node()
    )
    graph.add_node(
        WorkflowNode.agent(node_id="tail", agent_name="tester"),
    )
    graph.add_edge("h", "tail")

    executor = WorkflowExecutor(runtime=MockRuntime())
    first = executor.run(graph, session_id="s")

    assert first.status == WorkflowRunStatus.WAITING_APPROVAL

    second = executor.resume(
        first.run_id,
        approval_payload={
            "action": ApprovalAction.REJECT.value,
            "comment": "not ready",
        },
    )

    assert second.status == WorkflowRunStatus.FAILED
    assert len(second.node_results["h"].error) > 0


def test_human_node_modify_prompt_reaches_reviewer() -> None:
    graph = build_team_human_approval_workflow()
    graph.validate()

    runtime = MockRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    paused = executor.run(
        graph,
        session_id="sess",
        user_message="build feature X",
    )

    assert paused.status == WorkflowRunStatus.WAITING_APPROVAL
    assert paused.pending_node_id == "human_gate"
    assert len(runtime.calls) == 2
    assert runtime.calls[0].agent_name == "manager"
    assert runtime.calls[1].agent_name == "developer"

    done = executor.resume(
        paused.run_id,
        approval_payload={
            "action": ApprovalAction.MODIFY.value,
            "modified_prompt": "Focus on security and error handling",
        },
    )

    assert done.status == WorkflowRunStatus.COMPLETED
    assert len(runtime.calls) == 4

    reviewer_task = runtime.calls[2]
    assert reviewer_task.agent_name == "reviewer"
    assert "security" in reviewer_task.user_message
    assert "output-from-developer" in reviewer_task.user_message

    assert runtime.calls[3].agent_name == "tester"


def test_team_workflow_graph_structure() -> None:
    graph = build_team_human_approval_workflow()
    graph.validate()
    assert graph.entry_node_id == "manager"
    assert "human_gate" in graph.nodes
    assert len(graph.nodes) == 5
