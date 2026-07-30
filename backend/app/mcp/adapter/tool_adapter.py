from typing import Any

from app.mcp.clients.base import MCPClient
from app.mcp.error_handler import MCPErrorHandler
from app.mcp.types import MCPToolDefinition
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class MCPToolAdapter(BaseTool):
    """
    将 MCP Tool 适配为项目统一的 BaseTool。

    ChatAgent / ToolManager 无需知道 Tool 来自本地还是 MCP。
    """

    def __init__(
        self,
        client: MCPClient,
        definition: MCPToolDefinition,
        error_handler: MCPErrorHandler | None = None,
    ):

        self._client = client
        self._definition = definition
        self._error_handler = (
            error_handler or MCPErrorHandler()
        )

    @property
    def server_name(self) -> str:

        return self._client.server_name

    @property
    def mcp_tool_name(self) -> str:

        return self._definition.name

    @property
    def name(self) -> str:

        return (
            f"{self._client.server_name}."
            f"{self._definition.name}"
        )

    @property
    def description(self) -> str:

        return self._definition.description

    @property
    def schema(self) -> dict[str, Any]:

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._definition.description,
                "parameters": self._definition.input_schema
                or {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        try:

            result = self._error_handler.safe_call(
                self._client.server_name,
                f"call_tool:{self._definition.name}",
                lambda: self._client.call_tool(
                    self._definition.name,
                    context.arguments,
                ),
            )

            return ToolResult(
                success=result.success and not result.is_error,
                content=result.content,
            )

        except Exception as error:

            return self._error_handler.handle_tool_call_error(
                error,
                self._definition.name,
                self._client.server_name,
            )
