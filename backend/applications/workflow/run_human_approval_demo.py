"""
Task 6.3 Human Approval Demo。

流程: Manager → Developer → Human Approval → Reviewer → Tester
演示: 暂停 → 修改 Prompt 批准 → 继续执行

运行:
    cd backend
    python -m applications.workflow.run_human_approval_demo
"""

from __future__ import annotations

from typing import Any

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.workflow.base import WorkflowRunStatus
from app.workflow.examples.team_human_approval_workflow import (
    build_team_human_approval_workflow,
)
from app.workflow.executor import WorkflowExecutor
from app.workflow.human_node import ApprovalAction


class DemoRuntime:
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
        role = task.agent_name
        preview = task.user_message.replace("\n", " ")[:72]
        print(f"  [Agent:{role}] {preview}...")
        return AgentResult(
            success=True,
            model="demo",
            content=f"({role}) completed work",
        )


def run_approve_with_modified_prompt() -> None:
    print("\n=== 审批 Demo：暂停 → 修改 Prompt → 继续 ===")

    graph = build_team_human_approval_workflow()
    runtime = DemoRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    first = executor.run(
        graph,
        session_id="approval-demo",
        user_message="Implement user login MVP",
    )

    print(f"Workflow status: {first.status.value}")
    print(f"Pending node: {first.pending_node_id}")
    print(f"Approval prompt: {first.pending_message}")

    assert first.status == WorkflowRunStatus.WAITING_APPROVAL

    second = executor.resume(
        first.run_id,
        approval_payload={
            "action": ApprovalAction.MODIFY.value,
            "modified_prompt": (
                "Reviewer: prioritize auth edge cases and logging."
            ),
            "comment": "LGTM after security pass",
        },
    )

    print(f"Final status: {second.status.value}")
    print(f"Agents executed: {[c.agent_name for c in runtime.calls]}")
    reviewer_msg = runtime.calls[2].user_message
    print(f"Reviewer received modified prompt: {'auth edge' in reviewer_msg}")


def run_reject_path() -> None:
    print("\n=== 审批 Demo：拒绝 ===")

    graph = build_team_human_approval_workflow()
    runtime = DemoRuntime()
    executor = WorkflowExecutor(runtime=runtime)

    first = executor.run(
        graph,
        session_id="reject-demo",
        user_message="Quick patch",
    )

    assert first.status == WorkflowRunStatus.WAITING_APPROVAL

    rejected = executor.resume(
        first.run_id,
        approval_payload={
            "action": ApprovalAction.REJECT.value,
            "comment": "Need more tests from developer",
        },
    )

    print(f"Final status: {rejected.status.value}")
    print(f"Stopped after {len(runtime.calls)} agent runs (no reviewer/tester)")


def main() -> None:
    print("Human Approval Workflow Demo (Task 6.3)")
    run_approve_with_modified_prompt()
    run_reject_path()
    print("\nDemo finished.")


if __name__ == "__main__":
    main()
