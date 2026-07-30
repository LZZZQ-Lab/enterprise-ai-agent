"""
Database Tool Plugin — 数据访问扩展（示例）。
"""

from __future__ import annotations

from typing import Any

from app.plugins.base import PluginKind
from app.plugins.base import PluginMetadata
from app.plugins.base import ToolPlugin
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class DatabaseTool(BaseTool):
    @property
    def name(self) -> str:
        return "enterprise_database"

    @property
    def description(self) -> str:
        return "Run read-only SQL against enterprise DB (plugin demo)."

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["sql"],
                },
            },
        }

    def execute(self, context: ToolContext) -> ToolResult:
        sql = str(context.arguments.get("sql", "")).strip()
        limit = int(context.arguments.get("limit", 10))

        if not sql.lower().startswith("select"):
            return ToolResult(
                success=False,
                content="Only SELECT allowed in demo plugin",
            )

        rows = [
            {"id": 1, "name": "alpha"},
            {"id": 2, "name": "beta"},
        ][:limit]

        return ToolResult(
            success=True,
            content=f"SQL: {sql}\nrows={rows}",
        )


class DatabasePlugin(ToolPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="enterprise.database",
            name="Database Plugin",
            version="1.0.0",
            kind=PluginKind.TOOL,
            description="Read-only SQL demo tool",
            tags=("database", "sql"),
        )

    def tool(self) -> BaseTool:
        return DatabaseTool()


PLUGIN = DatabasePlugin()
