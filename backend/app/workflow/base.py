"""
Enterprise Workflow Engine — 基础类型与执行上下文。
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class OnFailureAction(str, Enum):
    FAIL = "fail"
    RETRY = "retry"
    SKIP = "skip"
    CONTINUE = "continue"


@dataclass
class NodeExecutionResult:
    node_id: str
    status: NodeRunStatus
    success: bool
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:

        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "success": self.success,
            "output": self.output,
            "data": dict(self.data),
            "error": self.error,
            "attempts": self.attempts,
        }


@dataclass
class WorkflowExecutionContext:
    """
    单次 Workflow 运行的可变状态（与 Agent Runtime 解耦）。
    """

    session_id: str
    run_id: str
    user_message: str = ""
    shared_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    node_results: dict[str, NodeExecutionResult] = field(
        default_factory=dict,
    )

    def set_node_output(
        self,
        node_id: str,
        result: NodeExecutionResult,
    ) -> None:

        self.node_results[node_id] = result

        prefix = f"node:{node_id}"

        self.shared_context[f"{prefix}:output"] = result.output
        self.shared_context[f"{prefix}:success"] = result.success

        if result.data:

            self.shared_context[f"{prefix}:data"] = dict(result.data)


@dataclass
class WorkflowRunResult:
    workflow_id: str
    run_id: str
    status: WorkflowRunStatus
    shared_context: dict[str, Any] = field(default_factory=dict)
    node_results: dict[str, NodeExecutionResult] = field(
        default_factory=dict,
    )
    error: str = ""
    pending_node_id: str | None = None
    pending_message: str = ""

    def to_dict(self) -> dict[str, Any]:

        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "status": self.status.value,
            "shared_context": dict(self.shared_context),
            "node_results": {
                key: value.to_dict()
                for key, value in self.node_results.items()
            },
            "error": self.error,
            "pending_node_id": self.pending_node_id,
            "pending_message": self.pending_message,
        }
