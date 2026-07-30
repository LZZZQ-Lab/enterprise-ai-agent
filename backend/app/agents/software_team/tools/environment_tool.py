"""
Task 5.7：Environment Tool — 管理 .env / .env.example（不含密钥落日志）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

ALLOWED_ENV_FILES = frozenset(
    {
        ".env.example",
        "deploy/.env.example",
        ".env.local.example",
    }
)


class EnvironmentTool(BaseTool):
    """
    读写环境模板文件（禁止直接写 .env 生产密钥）。
    """

    @property
    def name(self) -> str:

        return "environment"

    @property
    def description(self) -> str:

        return (
            "Manage environment template files (.env.example). "
            "Actions: read, write, upsert. "
            "Do not store production secrets; use placeholders."
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
                            "enum": ["read", "write", "upsert"],
                        },
                        "path": {
                            "type": "string",
                            "description": "Relative path, e.g. .env.example",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content for write",
                        },
                        "key": {
                            "type": "string",
                            "description": "For upsert: VAR_NAME",
                        },
                        "value": {
                            "type": "string",
                            "description": "For upsert: placeholder value",
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
            path = str(context.arguments.get("path", "")).strip().replace(
                "\\",
                "/",
            )

            file_path = _resolve_env_path(path)

            if action == "read":

                if not file_path.is_file():

                    return ToolResult(
                        success=False,
                        content=f"File not found: {path}",
                    )

                return ToolResult(
                    success=True,
                    content=file_path.read_text(encoding="utf-8"),
                )

            if action == "write":

                content = str(context.arguments.get("content", ""))

                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

                return ToolResult(
                    success=True,
                    content=f"Wrote {path} ({len(content)} chars)",
                )

            if action == "upsert":

                key = str(context.arguments.get("key", "")).strip()
                value = str(context.arguments.get("value", ""))

                if not key:

                    return ToolResult(
                        success=False,
                        content="key is required for upsert",
                    )

                lines: list[str] = []

                if file_path.is_file():

                    lines = file_path.read_text(encoding="utf-8").splitlines()

                replaced = False
                prefix = f"{key}="

                for index, line in enumerate(lines):

                    if line.startswith(prefix):

                        lines[index] = f"{key}={value}"
                        replaced = True
                        break

                if not replaced:

                    lines.append(f"{key}={value}")

                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(
                    "\n".join(lines) + "\n",
                    encoding="utf-8",
                )

                return ToolResult(
                    success=True,
                    content=f"Upserted {key} in {path}",
                )

            return ToolResult(
                success=False,
                content=f"Unknown action: {action}",
            )

        except Exception as error:

            return ToolResult(
                success=False,
                content=str(error),
            )


def _resolve_env_path(relative_path: str) -> Path:

    normalized = relative_path.replace("\\", "/").strip()

    if normalized.startswith("./"):

        normalized = normalized[2:]

    if normalized == ".env" or normalized.endswith("/.env"):

        raise ValueError(
            "Writing .env is not allowed; use .env.example with placeholders."
        )

    if normalized not in ALLOWED_ENV_FILES and not normalized.endswith(
        ".env.example"
    ):

        raise ValueError(
            f"Environment path not allowed: {relative_path}. "
            "Use .env.example or deploy/.env.example"
        )

    workspace = developer_workspace_ctx.get()

    if workspace is None:

        raise ValueError("Workspace is not set.")

    root = workspace.resolve()
    target = (root / normalized).resolve()

    if target != root and root not in target.parents:

        raise ValueError(f"Path escapes workspace: {relative_path}")

    return target
