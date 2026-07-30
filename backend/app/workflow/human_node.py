"""
Human Approval 节点（Task 6.3）。

支持：等待审批、批准、拒绝、修改下游 Prompt。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.workflow.base import NodeExecutionResult
from app.workflow.base import NodeRunStatus
from app.workflow.base import WorkflowExecutionContext
from app.workflow.node import NodeType
from app.workflow.node import WorkflowNode


class ApprovalAction(str, Enum):
    """人工审批动作。"""

    PENDING = "pending"
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


def approval_context_key(node_id: str) -> str:
    return f"approval:{node_id}"


def approval_flag_key(node_id: str) -> str:
    return f"{approval_context_key(node_id)}:approved"


def modified_prompt_key(node_id: str) -> str:
    return f"{approval_context_key(node_id)}:modified_prompt"


@dataclass
class HumanApprovalNode:
    """
    企业级人工审批节点定义与执行逻辑。
    """

    node_id: str
    prompt: str
    name: str = "Human Approval"
    allow_modify_prompt: bool = True
    context_prompt_key: str = "human_modified_prompt"

    def to_workflow_node(self) -> WorkflowNode:
        return WorkflowNode(
            id=self.node_id,
            type=NodeType.HUMAN_APPROVAL,
            name=self.name,
            config={
                "prompt": self.prompt,
                "allow_modify_prompt": self.allow_modify_prompt,
                "context_prompt_key": self.context_prompt_key,
            },
        )

    @classmethod
    def from_workflow_node(cls, node: WorkflowNode) -> HumanApprovalNode:
        if node.type != NodeType.HUMAN_APPROVAL:
            raise ValueError(f"Not a human approval node: {node.id}")

        return cls(
            node_id=node.id,
            prompt=str(node.config.get("prompt", "Approval required")),
            name=node.name or "Human Approval",
            allow_modify_prompt=bool(
                node.config.get("allow_modify_prompt", True),
            ),
            context_prompt_key=str(
                node.config.get("context_prompt_key", "human_modified_prompt"),
            ),
        )

    @staticmethod
    def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """
        统一审批载荷字段。

        支持:
        - approved / approve
        - action: approve | reject | modify
        - modified_prompt
        - comment
        """

        data = dict(payload)
        action_raw = str(data.get("action", "")).lower().strip()

        if action_raw == ApprovalAction.REJECT.value:
            data["approved"] = False
        elif action_raw == ApprovalAction.APPROVE.value:
            data["approved"] = True
        elif action_raw == ApprovalAction.MODIFY.value:
            data["approved"] = data.get("approved", True)

        if "approved" not in data and "approve" in data:
            data["approved"] = bool(data.get("approve"))

        modified = data.get("modified_prompt") or data.get("modified_message")

        if modified and action_raw != ApprovalAction.REJECT.value:
            if "approved" not in data:
                data["approved"] = True

            data["modified_prompt"] = str(modified)

        return data

    @classmethod
    def apply_payload(
        cls,
        context: WorkflowExecutionContext,
        node_id: str,
        payload: dict[str, Any],
        *,
        context_prompt_key: str = "human_modified_prompt",
    ) -> None:
        """
        写入审批结果到 shared_context（resume 时调用）。
        """

        normalized = cls.normalize_payload(payload)
        base_key = approval_context_key(node_id)

        context.shared_context[base_key] = normalized

        approved = bool(normalized.get("approved", False))
        context.shared_context[approval_flag_key(node_id)] = approved

        modified = normalized.get("modified_prompt")

        if modified:
            context.shared_context[modified_prompt_key(node_id)] = modified
            context.shared_context[context_prompt_key] = str(modified)
        elif approved:
            context.shared_context.setdefault(
                context_prompt_key,
                "Proceed with standard review.",
            )

        comment = normalized.get("comment")

        if comment:
            context.shared_context[f"{base_key}:comment"] = str(comment)

    def evaluate(
        self,
        context: WorkflowExecutionContext,
    ) -> NodeExecutionResult:
        """
        首次进入：WAITING_APPROVAL；resume 后：根据批准/拒绝/修改继续。
        """

        base_key = approval_context_key(self.node_id)
        payload = context.shared_context.get(base_key)

        if payload is None:
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeRunStatus.WAITING_APPROVAL,
                success=False,
                output=self.prompt,
                data={
                    "awaiting": True,
                    "allow_modify_prompt": self.allow_modify_prompt,
                    "actions": [
                        ApprovalAction.APPROVE.value,
                        ApprovalAction.REJECT.value,
                        ApprovalAction.MODIFY.value,
                    ],
                },
            )

        approved = bool(
            context.shared_context.get(
                approval_flag_key(self.node_id),
                False,
            )
        )

        if not approved:
            comment = context.shared_context.get(f"{base_key}:comment", "")
            detail = f"Rejected by human reviewer"

            if comment:
                detail = f"{detail}: {comment}"

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeRunStatus.FAILED,
                success=False,
                output=detail,
                error="approval_rejected",
                data={"approved": False},
            )

        modified = context.shared_context.get(
            modified_prompt_key(self.node_id),
            "",
        )

        output = "Approved"

        if modified:
            output = f"Approved with modified prompt: {modified}"

        return NodeExecutionResult(
            node_id=self.node_id,
            status=NodeRunStatus.COMPLETED,
            success=True,
            output=output,
            data={
                "approved": True,
                "modified_prompt": modified,
            },
        )


def human_approval_workflow_node(
    *,
    node_id: str,
    prompt: str,
    name: str = "Human Approval",
    allow_modify_prompt: bool = True,
) -> WorkflowNode:
    """便捷工厂，与 WorkflowNode.human_approval 对齐。"""

    return HumanApprovalNode(
        node_id=node_id,
        prompt=prompt,
        name=name,
        allow_modify_prompt=allow_modify_prompt,
    ).to_workflow_node()
