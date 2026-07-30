#!/usr/bin/env python3
"""
Demo 04 — Workflow 执行

Part A: 线性 Agent DAG（product → architecture）
Part B: 人工审批节点（暂停 → 修改 Prompt → 继续）

全程 Mock Runtime，无需 LLM / Docker。

用法:
    python examples/demo_04_workflow.py
"""

from __future__ import annotations

from typing import Any

from _bootstrap import bootstrap


class MockWorkflowRuntime:
    """Records AgentTask calls and returns deterministic outputs."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(
        self,
        task,
        *,
        config=None,
        **kwargs: Any,
    ):
        from app.agents.types import AgentResult

        role = task.agent_name
        self.calls.append(role)
        preview = (task.user_message or "").replace("\n", " ")[:60]
        print(f"  → Agent [{role}] {preview}...")

        return AgentResult(
            success=True,
            model="workflow-mock",
            content=f"({role}) mock output",
        )


def demo_linear_workflow() -> None:
    from app.workflow.base import WorkflowRunStatus
    from app.workflow.executor import WorkflowExecutor
    from app.workflow.graph import WorkflowGraph
    from app.workflow.node import WorkflowNode

    print("--- Part A: 线性 Workflow (product → architecture) ---\n")

    graph = WorkflowGraph(id="demo-linear", entry_node_id="product")
    graph.add_node(
        WorkflowNode.agent(
            node_id="product",
            agent_name="product",
            name="Product PRD",
            message_template="{user_message}",
        )
    )
    graph.add_node(
        WorkflowNode.agent(
            node_id="architecture",
            agent_name="architecture",
            name="Architecture",
            message_template="Design from PRD:\n{node:product:output}",
        )
    )
    graph.add_edge("product", "architecture")

    runtime = MockWorkflowRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    result = executor.run(
        graph,
        session_id="demo-04-linear",
        user_message="Build enterprise knowledge assistant MVP",
    )

    print(f"\nStatus  : {result.status.value}")
    print(f"Agents  : {runtime.calls}")
    assert result.status == WorkflowRunStatus.COMPLETED
    print()


def demo_human_approval() -> None:
    from app.workflow.base import WorkflowRunStatus
    from app.workflow.examples.team_human_approval_workflow import (
        build_team_human_approval_workflow,
    )
    from app.workflow.executor import WorkflowExecutor
    from app.workflow.human_node import ApprovalAction

    print("--- Part B: 人工审批 Workflow ---\n")

    graph = build_team_human_approval_workflow()
    runtime = MockWorkflowRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    first = executor.run(
        graph,
        session_id="demo-04-approval",
        user_message="Implement login MVP",
    )

    print(f"\nStatus (1): {first.status.value}")
    print(f"Pending   : {first.pending_node_id}")
    assert first.status == WorkflowRunStatus.WAITING_APPROVAL

    second = executor.resume(
        first.run_id,
        approval_payload={
            "action": ApprovalAction.MODIFY.value,
            "modified_prompt": "Reviewer: focus on auth edge cases.",
            "comment": "approved with edits",
        },
    )

    print(f"Status (2): {second.status.value}")
    print(f"Agents    : {runtime.calls}")
    assert second.status == WorkflowRunStatus.COMPLETED
    print()


def main() -> None:
    bootstrap()

    print("=== Demo 04: Workflow Engine [Mock] ===\n")

    demo_linear_workflow()
    demo_human_approval()

    print("Done.")


if __name__ == "__main__":
    main()
