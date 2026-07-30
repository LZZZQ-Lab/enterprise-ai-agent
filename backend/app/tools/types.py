from dataclasses import dataclass
from typing import Any


@dataclass
class ToolContext:
    """
    Tool 执行上下文
    """

    tool_name: str

    arguments: dict[str, Any]

    approval_token: str | None = None


@dataclass
class ToolResult:
    """
    Tool 执行结果
    """

    success: bool

    content: str