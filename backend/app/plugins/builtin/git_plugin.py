"""
Git Tool Plugin — 版本控制扩展（示例）。
"""

from __future__ import annotations

from typing import Any

from app.plugins.base import PluginKind
from app.plugins.base import PluginMetadata
from app.plugins.base import ToolPlugin
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class GitTool(BaseTool):
    @property
    def name(self) -> str:
        return "enterprise_git"

    @property
    def description(self) -> str:
        return "Git operations (status, diff summary) — plugin demo."

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
                        "action": {
                            "type": "string",
                            "enum": ["status", "diff_stat"],
                        },
                        "path": {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        }

    def execute(self, context: ToolContext) -> ToolResult:
        action = str(context.arguments.get("action", "status"))
        path = str(context.arguments.get("path", "."))

        if action == "diff_stat":
            body = f"3 files changed, 42 insertions(+), 7 deletions(-) [{path}]"
        else:
            body = f"On branch main\nYour branch is up to date.\n  path: {path}"

        return ToolResult(success=True, content=body)


class GitPlugin(ToolPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="enterprise.git",
            name="Git Plugin",
            version="1.0.0",
            kind=PluginKind.TOOL,
            description="Git status / diff demo tool",
            tags=("git", "vcs"),
        )

    def tool(self) -> BaseTool:
        return GitTool()


PLUGIN = GitPlugin()
