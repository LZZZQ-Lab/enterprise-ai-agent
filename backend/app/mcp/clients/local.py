from typing import Any

from app.mcp.clients.base import MCPClient
from app.mcp.exceptions import MCPNotConnectedError
from app.mcp.exceptions import MCPPromptNotFoundError
from app.mcp.exceptions import MCPResourceNotFoundError
from app.mcp.exceptions import MCPToolNotFoundError
from app.mcp.types import MCPPromptDefinition
from app.mcp.types import MCPPromptMessage
from app.mcp.types import MCPPromptResult
from app.mcp.types import MCPResourceContent
from app.mcp.types import MCPResourceInfo
from app.mcp.types import MCPToolCallResult
from app.mcp.types import MCPToolDefinition


class LocalMCPClient(MCPClient):
    """
    本地 Mock MCP Client。
    """

    _MOCK_TOOLS: dict[str, MCPToolDefinition] = {
        "get_current_time": MCPToolDefinition(
            name="get_current_time",
            description="Get the current server time.",
            input_schema={
                "type": "object",
                "properties": {},
            },
        ),
        "echo": MCPToolDefinition(
            name="echo",
            description="Echo back the input message.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo.",
                    }
                },
                "required": ["message"],
            },
        ),
    }

    _MOCK_RESOURCES: dict[str, MCPResourceInfo] = {
        "file://company/policy.md": MCPResourceInfo(
            uri="file://company/policy.md",
            name="Leave Policy",
            description="Company leave policy document.",
            mime_type="text/markdown",
            metadata={"department": "HR"},
        ),
    }

    _MOCK_RESOURCE_CONTENT: dict[str, str] = {
        "file://company/policy.md": (
            "# Leave Policy\n\n"
            "Employees are entitled to 15 days of annual leave."
        ),
    }

    _MOCK_PROMPTS: dict[str, MCPPromptDefinition] = {
        "support_assistant": MCPPromptDefinition(
            name="support_assistant",
            description="Prompt template for support assistant.",
            arguments=[
                {
                    "name": "topic",
                    "description": "Support topic",
                    "required": True,
                }
            ],
        ),
    }

    def __init__(
        self,
        server_name: str = "local-mock",
    ) -> None:

        self._server_name = server_name
        self._connected = False

    @property
    def server_name(self) -> str:

        return self._server_name

    @property
    def is_connected(self) -> bool:

        return self._connected

    def connect(self) -> None:

        self._connected = True

    def disconnect(self) -> None:

        self._connected = False

    def _ensure_connected(self) -> None:

        if not self._connected:

            raise MCPNotConnectedError(
                f"MCP server '{self._server_name}' is not connected."
            )

    def list_tools(self) -> list[MCPToolDefinition]:

        self._ensure_connected()

        return list(self._MOCK_TOOLS.values())

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        self._ensure_connected()

        if name not in self._MOCK_TOOLS:

            raise MCPToolNotFoundError(
                f"MCP tool '{name}' not found on "
                f"server '{self._server_name}'."
            )

        if name == "get_current_time":

            return MCPToolCallResult(
                success=True,
                content="2026-07-08 00:00:00 UTC",
            )

        if name == "echo":

            message = arguments.get(
                "message",
                "",
            )

            return MCPToolCallResult(
                success=True,
                content=f"Echo: {message}",
            )

        return MCPToolCallResult(
            success=False,
            content=f"Unknown mock tool '{name}'.",
            is_error=True,
        )

    def list_resources(self) -> list[MCPResourceInfo]:

        self._ensure_connected()

        return list(self._MOCK_RESOURCES.values())

    def read_resource(
        self,
        uri: str,
    ) -> MCPResourceContent:

        self._ensure_connected()

        if uri not in self._MOCK_RESOURCES:

            raise MCPResourceNotFoundError(
                f"MCP resource '{uri}' not found on "
                f"server '{self._server_name}'."
            )

        resource = self._MOCK_RESOURCES[uri]

        return MCPResourceContent(
            uri=uri,
            content=self._MOCK_RESOURCE_CONTENT[uri],
            mime_type=resource.mime_type,
        )

    def list_prompts(self) -> list[MCPPromptDefinition]:

        self._ensure_connected()

        return list(self._MOCK_PROMPTS.values())

    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPPromptResult:

        self._ensure_connected()

        if name not in self._MOCK_PROMPTS:

            raise MCPPromptNotFoundError(
                f"MCP prompt '{name}' not found on "
                f"server '{self._server_name}'."
            )

        args = arguments or {}
        topic = args.get(
            "topic",
            "general",
        )

        return MCPPromptResult(
            name=name,
            description=self._MOCK_PROMPTS[name].description,
            messages=[
                MCPPromptMessage(
                    role="system",
                    content=(
                        "You are a helpful support assistant "
                        f"for topic: {topic}."
                    ),
                )
            ],
        )
