from app.mcp.clients.base import MCPClient
from app.mcp.clients.enterprise_demo import EnterpriseDemoMCPClient
from app.mcp.clients.local import LocalMCPClient

__all__ = [
    "MCPClient",
    "LocalMCPClient",
    "EnterpriseDemoMCPClient",
    "create_mcp_client",
]

_CLIENT_ALIASES = {
    "local-mock": LocalMCPClient,
    "local": LocalMCPClient,
    "enterprise-demo": EnterpriseDemoMCPClient,
    "demo": EnterpriseDemoMCPClient,
}


def create_mcp_client(
    server_name: str,
    **kwargs,
) -> MCPClient:
    """
    按名称创建 MCP Client（Demo / Mock / 后续 STDIO）。
    """

    key = server_name.lower().strip()

    factory = _CLIENT_ALIASES.get(key)

    if factory is None:

        if key.startswith("enterprise"):

            return EnterpriseDemoMCPClient(
                server_name=server_name,
                **kwargs,
            )

        return LocalMCPClient(server_name=server_name)

    return factory(server_name=server_name, **kwargs)
