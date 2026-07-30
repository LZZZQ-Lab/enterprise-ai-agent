"""
Task 5.6/5.7：Terminal Tool — 工作区内受控命令（pytest / docker）。
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import Any

from app.agents.software_team.tools.terminal_policy import terminal_mode_ctx
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

MAX_OUTPUT_CHARS = 32_000
DEFAULT_TIMEOUT = 120
DEVOPS_TIMEOUT = 600


class TerminalTool(BaseTool):
    """
    在工作区根目录执行终端命令。
    模式由 terminal_mode_ctx 控制：pytest | devops。
    """

    @property
    def name(self) -> str:

        return "terminal"

    @property
    def description(self) -> str:

        mode = terminal_mode_ctx.get()

        if mode == "devops":

            return (
                "Run deployment commands in workspace. "
                "Allowed: docker build, docker compose build/up/down/config."
            )

        return (
            "Run pytest in workspace: "
            "pytest ... or python -m pytest ..."
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
                        "command": {
                            "type": "string",
                            "description": "Command to execute",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Max runtime seconds",
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        try:

            command_text = str(context.arguments.get("command", "")).strip()
            mode = terminal_mode_ctx.get()
            default_timeout = (
                DEVOPS_TIMEOUT if mode == "devops" else DEFAULT_TIMEOUT
            )

            timeout = int(
                context.arguments.get("timeout_seconds", default_timeout)
            )

            workspace = developer_workspace_ctx.get()

            if workspace is None:

                raise ValueError("Workspace is not set.")

            argv = _build_argv(command_text, mode=mode)
            env = _workspace_env(workspace)

            completed = subprocess.run(
                argv,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
            )

            combined = (
                (completed.stdout or "")
                + ("\n" if completed.stdout and completed.stderr else "")
                + (completed.stderr or "")
            )

            if len(combined) > MAX_OUTPUT_CHARS:

                combined = (
                    combined[:MAX_OUTPUT_CHARS]
                    + f"\n...[truncated, total {len(combined)} chars]"
                )

            status = f"exit_code={completed.returncode}"

            return ToolResult(
                success=completed.returncode == 0,
                content=f"{status}\n{combined}",
            )

        except subprocess.TimeoutExpired:

            return ToolResult(
                success=False,
                content="Command timed out.",
            )

        except Exception as error:

            return ToolResult(
                success=False,
                content=str(error),
            )


def _build_argv(command_text: str, *, mode: str) -> list[str]:

    if not command_text:

        raise ValueError("command is required.")

    if ";" in command_text or "|" in command_text or "&" in command_text:

        raise ValueError("Shell operators are not allowed.")

    lowered = command_text.lower().strip()

    if mode == "devops":

        if not _is_devops_command(lowered):

            raise ValueError(
                "DevOps mode allows: docker build, docker compose ..."
            )

    elif not (
        lowered.startswith("pytest")
        or lowered.startswith("python -m pytest")
        or lowered.startswith(f"{sys.executable.lower()} -m pytest")
    ):

        raise ValueError(
            "Pytest mode allows: pytest ... or python -m pytest ..."
        )

    parts = shlex.split(command_text, posix=os.name != "nt")

    if parts and parts[0] == "python":

        parts[0] = sys.executable

    return parts


def _is_devops_command(lowered: str) -> bool:

    prefixes = (
        "docker build",
        "docker compose",
        "docker-compose",
    )

    return any(lowered.startswith(prefix) for prefix in prefixes)


def _workspace_env(workspace) -> dict[str, str]:

    env = os.environ.copy()
    root = str(workspace.resolve())
    existing = env.get("PYTHONPATH", "")

    env["PYTHONPATH"] = (
        f"{root}{os.pathsep}{existing}" if existing else root
    )

    return env
