from typing import TYPE_CHECKING

from app.core.logger import logger
from app.mcp.adapter.tool_adapter import MCPToolAdapter
from app.mcp.clients.base import MCPClient
from app.mcp.error_handler import MCPErrorHandler
from app.mcp.exceptions import MCPConnectionError
from app.mcp.prompt_provider import MCPPromptProvider
from app.mcp.resource import MCPResource
from app.mcp.resource import MCPResourceProvider
from app.mcp.types import MCPPromptDefinition
from app.mcp.types import MCPPromptResult
from app.mcp.types import MCPResourceContent
from app.tools.base_tool import BaseTool

if TYPE_CHECKING:
    pass


class MCPServerResourceProvider(MCPResourceProvider):
    """
    基于 MCPServerManager 的 Resource Provider。
    """

    def __init__(
        self,
        server_manager: "MCPServerManager",
        error_handler: MCPErrorHandler | None = None,
    ):

        self._server_manager = server_manager
        self._error_handler = (
            error_handler or MCPErrorHandler()
        )

    def list_resources(self) -> list[MCPResource]:

        return self._server_manager.get_all_resources()

    def read_resource(
        self,
        resource_id: str,
    ) -> MCPResourceContent:

        server_name, uri = self._parse_resource_id(
            resource_id
        )

        client = self._server_manager.get_server(
            server_name
        )

        try:

            return self._error_handler.safe_call(
                server_name,
                f"read_resource:{uri}",
                lambda: client.read_resource(uri),
            )

        except Exception as error:

            content = self._error_handler.handle_resource_not_found(
                resource_id,
                server_name,
            )

            return MCPResourceContent(
                uri=uri,
                content=content,
            )

    @staticmethod
    def _parse_resource_id(
        resource_id: str,
    ) -> tuple[str, str]:

        if "|" not in resource_id:

            raise ValueError(
                f"Invalid MCP resource id: {resource_id}"
            )

        server_name, uri = resource_id.split(
            "|",
            maxsplit=1,
        )

        return server_name, uri


class MCPServerPromptProvider(MCPPromptProvider):
    """
    基于 MCPServerManager 的 Prompt Provider。
    """

    def __init__(
        self,
        server_manager: "MCPServerManager",
        error_handler: MCPErrorHandler | None = None,
    ):

        self._server_manager = server_manager
        self._error_handler = (
            error_handler or MCPErrorHandler()
        )

    def list_prompts(self) -> list[MCPPromptDefinition]:

        prompts: list[MCPPromptDefinition] = []

        for client in self._server_manager.get_all_servers():

            prompts.extend(
                client.list_prompts()
            )

        return prompts

    def get_prompt(
        self,
        name: str,
        arguments: dict | None = None,
    ) -> MCPPromptResult:

        server_name, prompt_name = self._parse_prompt_name(
            name
        )

        client = self._server_manager.get_server(
            server_name
        )

        return self._error_handler.safe_call(
            server_name,
            f"get_prompt:{prompt_name}",
            lambda: client.get_prompt(
                prompt_name,
                arguments,
            ),
        )

    @staticmethod
    def _parse_prompt_name(
        name: str,
    ) -> tuple[str, str]:

        if "." not in name:

            raise ValueError(
                f"Invalid MCP prompt name: {name}"
            )

        server_name, prompt_name = name.split(
            ".",
            maxsplit=1,
        )

        return server_name, prompt_name


class MCPServerManager:
    """
    MCP Server 管理器。

    负责注册/删除 Server，聚合 Tool / Resource / Prompt。
    支持未来 Multi Server 调度、Health Check、OAuth 等扩展。
    """

    def __init__(
        self,
        error_handler: MCPErrorHandler | None = None,
    ):

        self._error_handler = (
            error_handler or MCPErrorHandler()
        )

        self._servers: dict[str, MCPClient] = {}

        self._tool_adapters: dict[str, MCPToolAdapter] = {}

    def register_server(
        self,
        client: MCPClient,
    ) -> None:

        try:

            self._error_handler.safe_call(
                client.server_name,
                "connect",
                client.connect,
            )

        except Exception as error:

            self._error_handler.handle_connection_error(
                error,
                client.server_name,
            )

        self._servers[client.server_name] = client

        logger.info(
            "MCP server registered: %s",
            client.server_name,
        )

    def unregister_server(
        self,
        server_name: str,
    ) -> None:

        client = self._servers.pop(
            server_name,
            None,
        )

        if client is None:

            return

        try:

            client.disconnect()

        except Exception as error:

            logger.warning(
                "MCP server '%s' disconnect error: %s",
                server_name,
                error,
            )

        self._tool_adapters = {
            name: adapter
            for name, adapter in self._tool_adapters.items()
            if adapter.server_name != server_name
        }

        logger.info(
            "MCP server unregistered: %s",
            server_name,
        )

    def get_server(
        self,
        server_name: str,
    ) -> MCPClient:

        if server_name not in self._servers:

            raise MCPConnectionError(
                f"MCP server '{server_name}' is not registered."
            )

        return self._servers[server_name]

    def get_all_servers(self) -> list[MCPClient]:

        return list(self._servers.values())

    def discover_tools(self) -> list[BaseTool]:

        adapters: list[BaseTool] = []
        new_adapters: dict[str, MCPToolAdapter] = {}

        for client in self._servers.values():

            for definition in client.list_tools():

                adapter = MCPToolAdapter(
                    client=client,
                    definition=definition,
                    error_handler=self._error_handler,
                )

                new_adapters[adapter.name] = adapter

                adapters.append(adapter)

        self._tool_adapters = new_adapters

        return adapters

    def get_all_tools(self) -> list[BaseTool]:

        return list(self._tool_adapters.values())

    def get_tool(
        self,
        tool_name: str,
    ) -> BaseTool | None:

        return self._tool_adapters.get(tool_name)

    def get_all_resources(self) -> list[MCPResource]:

        resources: list[MCPResource] = []

        for client in self._servers.values():

            for info in client.list_resources():

                resources.append(
                    MCPResource(
                        id=f"{client.server_name}|{info.uri}",
                        name=info.name,
                        description=info.description,
                        metadata=info.metadata,
                        server_name=client.server_name,
                        uri=info.uri,
                    )
                )

        return resources

    @property
    def resource_provider(self) -> MCPServerResourceProvider:

        return MCPServerResourceProvider(
            server_manager=self,
            error_handler=self._error_handler,
        )

    @property
    def prompt_provider(self) -> MCPServerPromptProvider:

        return MCPServerPromptProvider(
            server_manager=self,
            error_handler=self._error_handler,
        )
