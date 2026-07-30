from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.mcp.clients.base import MCPClient
from app.mcp.exceptions import MCPNotConnectedError
from app.mcp.exceptions import MCPToolNotFoundError
from app.mcp.types import MCPPromptDefinition
from app.mcp.types import MCPPromptResult
from app.mcp.types import MCPResourceContent
from app.mcp.types import MCPResourceInfo
from app.mcp.types import MCPToolCallResult
from app.mcp.types import MCPToolDefinition


class EnterpriseDemoMCPClient(MCPClient):
    """
    企业 MCP Demo Server（模拟外部系统）。

    能力域：文件系统、数据库、Git 仓库。
    后续可替换为真实 MCP STDIO/HTTP Server。
    """

    _TOOLS: dict[str, MCPToolDefinition] = {
        "fs_read_file": MCPToolDefinition(
            name="fs_read_file",
            description=(
                "Read a text file from the enterprise workspace "
                "(filesystem integration)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path",
                    }
                },
                "required": ["path"],
            },
        ),
        "fs_list_directory": MCPToolDefinition(
            name="fs_list_directory",
            description="List files in a workspace directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path",
                    }
                },
                "required": ["path"],
            },
        ),
        "db_query": MCPToolDefinition(
            name="db_query",
            description=(
                "Run a read-only SQL query against the demo "
                "enterprise database."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SELECT query",
                    }
                },
                "required": ["sql"],
            },
        ),
        "git_status": MCPToolDefinition(
            name="git_status",
            description=(
                "Get Git working tree status for a repository path."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Repository path",
                    }
                },
                "required": ["repo_path"],
            },
        ),
        "git_log": MCPToolDefinition(
            name="git_log",
            description="Get recent Git commit log (demo).",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                    },
                    "limit": {
                        "type": "integer",
                    },
                },
                "required": ["repo_path"],
            },
        ),
    }

    _MOCK_DB_ROWS: list[dict[str, Any]] = [
        {
            "project_id": "P-001",
            "name": "Enterprise AI Agent",
            "status": "active",
        },
        {
            "project_id": "P-002",
            "name": "Knowledge Base Rollout",
            "status": "planning",
        },
    ]

    _MOCK_GIT_LOG: list[str] = [
        "a1b2c3d feat: add MCP adapter",
        "d4e5f6g fix: tool registry sync",
    ]

    def __init__(
        self,
        server_name: str = "enterprise-demo",
        workspace_root: str | Path | None = None,
    ) -> None:

        self._server_name = server_name

        default_root = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "fixtures"
            / "mcp_demo"
            / "workspace"
        )

        self._workspace = Path(
            workspace_root or default_root
        ).resolve()

        self._connected = False

    @property
    def server_name(self) -> str:

        return self._server_name

    @property
    def is_connected(self) -> bool:

        return self._connected

    def connect(self) -> None:

        self._workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._connected = True

    def disconnect(self) -> None:

        self._connected = False

    def list_tools(self) -> list[MCPToolDefinition]:

        self._ensure_connected()

        return list(self._TOOLS.values())

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        self._ensure_connected()

        if name not in self._TOOLS:

            raise MCPToolNotFoundError(
                f"Tool '{name}' not found on {self._server_name}"
            )

        if name == "fs_read_file":

            return self._fs_read_file(arguments)

        if name == "fs_list_directory":

            return self._fs_list_directory(arguments)

        if name == "db_query":

            return self._db_query(arguments)

        if name == "git_status":

            return self._git_status(arguments)

        if name == "git_log":

            return self._git_log(arguments)

        return MCPToolCallResult(
            success=False,
            content=f"Unhandled tool {name}",
            is_error=True,
        )

    def list_resources(self) -> list[MCPResourceInfo]:

        self._ensure_connected()

        return [
            MCPResourceInfo(
                uri="file://workspace/README.md",
                name="Workspace README",
                description="Demo workspace index",
                mime_type="text/markdown",
            )
        ]

    def read_resource(
        self,
        uri: str,
    ) -> MCPResourceContent:

        self._ensure_connected()

        if uri.endswith("README.md"):

            path = self._workspace / "README.md"

            if path.is_file():

                return MCPResourceContent(
                    uri=uri,
                    content=path.read_text(encoding="utf-8"),
                    mime_type="text/markdown",
                )

        return MCPResourceContent(
            uri=uri,
            content="Resource not found in demo workspace.",
        )

    def list_prompts(self) -> list[MCPPromptDefinition]:

        self._ensure_connected()

        return []

    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPPromptResult:

        self._ensure_connected()

        return MCPPromptResult(name=name, messages=[])

    def _ensure_connected(self) -> None:

        if not self._connected:

            raise MCPNotConnectedError(
                f"MCP server '{self._server_name}' is not connected."
            )

    def _resolve_path(
        self,
        relative: str,
    ) -> Path:

        candidate = (self._workspace / relative).resolve()

        if not str(candidate).startswith(str(self._workspace)):

            raise ValueError("Path escapes workspace root.")

        return candidate

    def _fs_read_file(
        self,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        path = self._resolve_path(
            str(arguments.get("path", ""))
        )

        if not path.is_file():

            return MCPToolCallResult(
                success=False,
                content=f"File not found: {path.name}",
                is_error=True,
            )

        return MCPToolCallResult(
            success=True,
            content=path.read_text(encoding="utf-8"),
        )

    def _fs_list_directory(
        self,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        path = self._resolve_path(
            str(arguments.get("path", "."))
        )

        if not path.is_dir():

            return MCPToolCallResult(
                success=False,
                content=f"Not a directory: {path}",
                is_error=True,
            )

        entries = sorted(
            item.name for item in path.iterdir()
        )

        return MCPToolCallResult(
            success=True,
            content=json.dumps(entries, ensure_ascii=False),
        )

    def _db_query(
        self,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        sql = str(arguments.get("sql", "")).strip().lower()

        if not sql.startswith("select"):

            return MCPToolCallResult(
                success=False,
                content="Only SELECT queries allowed in demo DB.",
                is_error=True,
            )

        return MCPToolCallResult(
            success=True,
            content=json.dumps(
                self._MOCK_DB_ROWS,
                ensure_ascii=False,
                indent=2,
            ),
        )

    def _git_status(
        self,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        repo = str(arguments.get("repo_path", "enterprise-ai-agent"))

        body = (
            f"On branch main\n"
            f"Repository: {repo}\n"
            "Changes not staged:\n"
            "  modified: docs/roadmap.md\n"
            "Untracked files:\n"
            "  applications/mcp_demo/\n"
        )

        return MCPToolCallResult(
            success=True,
            content=body,
        )

    def _git_log(
        self,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        limit = int(arguments.get("limit") or 5)

        lines = self._MOCK_GIT_LOG[:limit]

        return MCPToolCallResult(
            success=True,
            content="\n".join(lines),
        )
