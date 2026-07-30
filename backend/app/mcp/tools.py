from __future__ import annotations

from pathlib import Path

from app.core.logger import logger
from app.mcp.adapter import adapt_servers_tools
from app.mcp.client import create_mcp_client
from app.mcp.server_manager import MCPServerManager
from app.tools.base_tool import BaseTool
from app.tools.registry import ToolRegistry


class MCPToolRegistryBridge:
    """
    MCP Server → Adapter → ToolRegistry → Agent。

    负责连接 Demo/企业 MCP Server，并把适配后的 Tool 注册到内部 Registry。
    """

    def __init__(
        self,
        manager: MCPServerManager | None = None,
    ) -> None:

        self._manager = manager or MCPServerManager()
        self._registered_names: list[str] = []

    @property
    def manager(self) -> MCPServerManager:

        return self._manager

    def register_server(
        self,
        server_name: str,
        **client_kwargs,
    ) -> None:

        client = create_mcp_client(
            server_name,
            **client_kwargs,
        )

        self._manager.register_server(client)

    def register_demo_enterprise_server(
        self,
        workspace_root: str | Path | None = None,
    ) -> None:

        self.register_server(
            "enterprise-demo",
            workspace_root=workspace_root,
        )

    def discover_adapted_tools(self) -> list[BaseTool]:

        clients = self._manager.get_all_servers()

        return adapt_servers_tools(clients)

    def sync_to_tool_registry(
        self,
        *,
        replace: bool = True,
    ) -> list[str]:
        """
        将 MCP Tool 写入 ToolRegistry，供 Agent ToolManager 使用。
        """

        if replace:

            self.unregister_from_tool_registry()

        tools = self.discover_adapted_tools()

        names: list[str] = []

        for tool in tools:

            ToolRegistry.register(tool)
            names.append(tool.name)

        self._registered_names = names

        logger.info(
            "MCP tools synced to ToolRegistry: %s",
            names,
        )

        return names

    def unregister_from_tool_registry(self) -> None:

        for name in self._registered_names:

            ToolRegistry._tools.pop(name, None)

        self._registered_names = []


def setup_enterprise_mcp_demo(
    workspace_root: str | Path | None = None,
) -> MCPToolRegistryBridge:
    """
    一键注册企业 MCP Demo 并同步 ToolRegistry。
    """

    bridge = MCPToolRegistryBridge()

    bridge.register_demo_enterprise_server(
        workspace_root=workspace_root,
    )

    bridge.sync_to_tool_registry()

    return bridge


__all__ = [
    "MCPToolRegistryBridge",
    "setup_enterprise_mcp_demo",
]
