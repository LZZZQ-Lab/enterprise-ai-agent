"""
Task 5.4：FileSystem Tool — 只读访问工作区（读架构、列目录）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

MAX_READ_CHARS = 48_000


def _resolve_workspace_path(relative_path: str) -> Path:

    workspace = developer_workspace_ctx.get()

    if workspace is None:

        raise ValueError(
            "Developer workspace is not set. "
            "Set metadata workspace_dir before run."
        )

    root = workspace.resolve()
    target = (root / relative_path).resolve()

    if target != root and root not in target.parents:

        raise ValueError(f"Path escapes workspace: {relative_path}")

    return target


class FileSystemTool(BaseTool):
    """
    工作区文件系统（只读）：read / list。
    禁止通过本 Tool 写入；写操作须使用 code Tool。
    """

    @property
    def name(self) -> str:

        return "filesystem"

    @property
    def description(self) -> str:

        return (
            "Read-only filesystem access in the project workspace. "
            "Actions: read (file content), list (directory tree). "
            "Do NOT use this tool to write or modify files."
        )

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
                            "enum": ["read", "list"],
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path, e.g. docs/architecture.md "
                                "or src/"
                            ),
                        },
                    },
                    "required": ["action", "path"],
                },
            },
        }

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        try:

            action = str(context.arguments.get("action", "")).strip()
            path = str(context.arguments.get("path", "")).strip()

            if action == "read":

                return self._read(path)

            if action == "list":

                return self._list(path or ".")

            return ToolResult(
                success=False,
                content=f"Unknown action: {action}",
            )

        except Exception as error:

            return ToolResult(
                success=False,
                content=str(error),
            )

    def _read(self, path: str) -> ToolResult:

        file_path = _resolve_workspace_path(path)

        if not file_path.is_file():

            return ToolResult(
                success=False,
                content=f"File not found: {path}",
            )

        content = file_path.read_text(encoding="utf-8")

        if len(content) > MAX_READ_CHARS:

            content = (
                content[:MAX_READ_CHARS]
                + f"\n...[truncated, total {len(content)} chars]"
            )

        return ToolResult(
            success=True,
            content=content,
        )

    def _list(self, directory: str) -> ToolResult:

        dir_path = _resolve_workspace_path(directory)

        if not dir_path.exists():

            return ToolResult(
                success=False,
                content=f"Directory not found: {directory}",
            )

        if dir_path.is_file():

            return ToolResult(
                success=True,
                content=dir_path.name,
            )

        files = sorted(
            str(item.relative_to(dir_path))
            for item in dir_path.rglob("*")
            if item.is_file()
        )

        if not files:

            return ToolResult(
                success=True,
                content=f"[{directory}] (empty)",
            )

        return ToolResult(
            success=True,
            content="\n".join(files[:500]),
        )
