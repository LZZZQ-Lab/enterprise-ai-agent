"""
Tool Calling 子系统（Task 9.1 canonical import）。

Implementation: ``backend/app/tools/``
"""

from app.tools.base_tool import BaseTool
from app.tools.factory import ToolFactory
from app.tools.manager import ToolManager
from app.tools.registry import ToolRegistry
from app.tools.time_tool import TimeTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

__all__ = [
    "BaseTool",
    "SearchKnowledgeTool",
    "TimeTool",
    "ToolContext",
    "ToolFactory",
    "ToolManager",
    "ToolRegistry",
    "ToolResult",
    "register_search_knowledge_tool",
    "reset_search_knowledge_tool_registration",
]


def __getattr__(name: str):
    if name == "SearchKnowledgeTool":
        from app.tools.knowledge_tool import SearchKnowledgeTool

        return SearchKnowledgeTool
    if name == "register_search_knowledge_tool":
        from app.tools.knowledge_tool import register_search_knowledge_tool

        return register_search_knowledge_tool
    if name == "reset_search_knowledge_tool_registration":
        from app.tools.knowledge_tool import (
            reset_search_knowledge_tool_registration,
        )

        return reset_search_knowledge_tool_registration
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
