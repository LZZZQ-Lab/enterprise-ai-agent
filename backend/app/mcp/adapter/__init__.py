from __future__ import annotations

from typing import TYPE_CHECKING

from app.mcp.adapter.tool_adapter import MCPToolAdapter
from app.mcp.error_handler import MCPErrorHandler
from app.tools.base_tool import BaseTool

if TYPE_CHECKING:

    from app.mcp.clients.base import MCPClient


def adapt_client_tools(
    client: MCPClient,
    *,
    error_handler: MCPErrorHandler | None = None,
) -> list[BaseTool]:

    handler = error_handler or MCPErrorHandler()

    return [
        MCPToolAdapter(
            client=client,
            definition=definition,
            error_handler=handler,
        )
        for definition in client.list_tools()
    ]


def adapt_servers_tools(
    clients: list[MCPClient],
    *,
    error_handler: MCPErrorHandler | None = None,
) -> list[BaseTool]:

    tools: list[BaseTool] = []

    for client in clients:

        tools.extend(
            adapt_client_tools(
                client,
                error_handler=error_handler,
            )
        )

    return tools


__all__ = [
    "MCPToolAdapter",
    "adapt_client_tools",
    "adapt_servers_tools",
]
