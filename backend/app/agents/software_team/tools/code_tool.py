"""
Task 5.4：Code Tool — 唯一允许修改工作区文件的入口。
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any

from app.agents.software_team.code_change_history import CodeChangeHistory
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

developer_history_ctx: ContextVar[CodeChangeHistory | None] = ContextVar(
    "developer_history_ctx",
    default=None,
)


def _resolve_workspace_path(relative_path: str) -> Path:

    workspace = developer_workspace_ctx.get()

    if workspace is None:

        raise ValueError("Developer workspace is not set.")

    root = workspace.resolve()
    target = (root / relative_path).resolve()

    if target != root and root not in target.parents:

        raise ValueError(f"Path escapes workspace: {relative_path}")

    return target


def _history() -> CodeChangeHistory:

    history = developer_history_ctx.get()

    if history is None:

        history = CodeChangeHistory()
        developer_history_ctx.set(history)

    return history


class CodeTool(BaseTool):
    """
    代码写入与补丁：write / search_replace / append。
    每次变更写入 CodeChangeHistory。
    """

    @property
    def name(self) -> str:

        return "code"

    @property
    def description(self) -> str:

        return (
            "Modify source files in the workspace. "
            "Actions: write (create/overwrite), search_replace, append. "
            "All project code changes MUST use this tool."
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
                            "enum": [
                                "write",
                                "search_replace",
                                "append",
                            ],
                        },
                        "path": {
                            "type": "string",
                            "description": "Relative file path",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full or appended content",
                        },
                        "old_string": {
                            "type": "string",
                            "description": (
                                "For search_replace: exact snippet to replace"
                            ),
                        },
                        "new_string": {
                            "type": "string",
                            "description": "Replacement text",
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

            if action == "write":

                return self._write(path, context.arguments)

            if action == "search_replace":

                return self._search_replace(path, context.arguments)

            if action == "append":

                return self._append(path, context.arguments)

            return ToolResult(
                success=False,
                content=f"Unknown action: {action}",
            )

        except Exception as error:

            return ToolResult(
                success=False,
                content=str(error),
            )

    def _write(
        self,
        path: str,
        arguments: dict[str, Any],
    ) -> ToolResult:

        content = str(arguments.get("content", ""))
        file_path = _resolve_workspace_path(path)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        _history().record(
            path=path,
            operation="write",
            tool="code",
            bytes_written=len(content.encode("utf-8")),
            summary=f"write {len(content)} chars",
        )

        return ToolResult(
            success=True,
            content=f"Wrote {path} ({len(content)} chars)",
        )

    def _append(
        self,
        path: str,
        arguments: dict[str, Any],
    ) -> ToolResult:

        content = str(arguments.get("content", ""))
        file_path = _resolve_workspace_path(path)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        existing = ""

        if file_path.is_file():

            existing = file_path.read_text(encoding="utf-8")

        file_path.write_text(
            existing + content,
            encoding="utf-8",
        )

        _history().record(
            path=path,
            operation="append",
            tool="code",
            bytes_written=len(content.encode("utf-8")),
            summary=f"append {len(content)} chars",
        )

        return ToolResult(
            success=True,
            content=f"Appended to {path} ({len(content)} chars)",
        )

    def _search_replace(
        self,
        path: str,
        arguments: dict[str, Any],
    ) -> ToolResult:

        old_string = str(arguments.get("old_string", ""))
        new_string = str(arguments.get("new_string", ""))

        if not old_string:

            return ToolResult(
                success=False,
                content="old_string is required for search_replace",
            )

        file_path = _resolve_workspace_path(path)

        if not file_path.is_file():

            return ToolResult(
                success=False,
                content=f"File not found: {path}",
            )

        text = file_path.read_text(encoding="utf-8")

        if old_string not in text:

            return ToolResult(
                success=False,
                content="old_string not found in file",
            )

        updated = text.replace(old_string, new_string, 1)
        file_path.write_text(updated, encoding="utf-8")

        _history().record(
            path=path,
            operation="search_replace",
            tool="code",
            bytes_written=len(new_string.encode("utf-8")),
            summary=f"replaced {len(old_string)} -> {len(new_string)} chars",
        )

        return ToolResult(
            success=True,
            content=f"Patched {path}",
        )
