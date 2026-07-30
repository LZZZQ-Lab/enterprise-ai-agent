"""
Workflow 节点定义。
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from uuid import uuid4


class NodeType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    HUMAN_APPROVAL = "human_approval"
    CONDITIONAL = "conditional"


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    name: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 0
    on_failure: str = "fail"

    @classmethod
    def agent(
        cls,
        *,
        node_id: str,
        agent_name: str,
        name: str = "",
        message_template: str = "{user_message}",
        max_retries: int = 0,
        on_failure: str = "fail",
        extra_metadata: dict[str, Any] | None = None,
    ) -> WorkflowNode:

        config = {
            "agent_name": agent_name,
            "message_template": message_template,
        }

        if extra_metadata:

            config["metadata"] = dict(extra_metadata)

        return cls(
            id=node_id,
            type=NodeType.AGENT,
            name=name or agent_name,
            config=config,
            max_retries=max_retries,
            on_failure=on_failure,
        )

    @classmethod
    def tool(
        cls,
        *,
        node_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        name: str = "",
    ) -> WorkflowNode:

        return cls(
            id=node_id,
            type=NodeType.TOOL,
            name=name or tool_name,
            config={
                "tool_name": tool_name,
                "arguments": dict(arguments or {}),
            },
        )

    @classmethod
    def human_approval(
        cls,
        *,
        node_id: str,
        prompt: str,
        name: str = "Human Approval",
        allow_modify_prompt: bool = True,
    ) -> WorkflowNode:

        from app.workflow.human_node import HumanApprovalNode

        return HumanApprovalNode(
            node_id=node_id,
            prompt=prompt,
            name=name,
            allow_modify_prompt=allow_modify_prompt,
        ).to_workflow_node()

    @classmethod
    def conditional(
        cls,
        *,
        node_id: str,
        source_key: str,
        equals: Any = True,
        name: str = "Conditional",
    ) -> WorkflowNode:

        return cls(
            id=node_id,
            type=NodeType.CONDITIONAL,
            name=name,
            config={
                "source_key": source_key,
                "equals": equals,
            },
        )


def new_node_id(prefix: str = "node") -> str:

    return f"{prefix}-{uuid4().hex[:8]}"
