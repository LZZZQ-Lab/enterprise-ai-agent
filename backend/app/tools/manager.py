from app.tools.factory import ToolFactory
from app.tools.registry import ToolRegistry
from app.tools.types import ToolContext
from app.tools.types import ToolResult

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.mcp.server_manager import MCPServerManager
    from app.config import AgentConfig
    from app.agents.executor.tracer import AgentTracer


class ToolManager:
    """
    Tool 管理器。

    统一管理本地 Tool 与 MCP Tool，对 ChatAgent 暴露统一接口。
    """

    def __init__(
        self,
        config: "AgentConfig | None" = None,
        mcp_server_manager: "MCPServerManager | None" = None,
        tracer: "AgentTracer | None" = None,
    ):

        from app.config import AgentConfig

        self._config = config or AgentConfig.from_env()
        self._mcp_server_manager = mcp_server_manager
        self._tracer = tracer
        self._mcp_tools: dict[str, object] = {}

        ToolFactory.initialize()

        if self._config.enable_knowledge_tool:

            from app.tools.knowledge_tool import (
                register_search_knowledge_tool,
            )

            register_search_knowledge_tool(
                default_top_k=self._config.top_k,
            )

        if (
            self._config.enable_mcp
            and self._mcp_server_manager is not None
            and self._config.auto_discover_tools
        ):

            self.refresh_mcp_tools()

    def bind_mcp(
        self,
        server_manager: "MCPServerManager",
    ) -> None:

        self._mcp_server_manager = server_manager

        if (
            self._config.enable_mcp
            and self._config.auto_discover_tools
        ):

            self.refresh_mcp_tools()

    def refresh_mcp_tools(self) -> None:

        if self._mcp_server_manager is None:

            return

        self._mcp_tools = {
            tool.name: tool
            for tool in self._mcp_server_manager.discover_tools()
        }

        if self._should_sync_mcp_to_registry():

            self._sync_mcp_tools_to_registry()

    def _should_sync_mcp_to_registry(self) -> bool:

        from app.config.settings import get_settings

        return get_settings().MCP_SYNC_TO_REGISTRY

    def _sync_mcp_tools_to_registry(self) -> None:

        for tool in self._mcp_tools.values():

            ToolRegistry.register(tool)

    def get_schemas(self) -> list[dict]:

        schemas = ToolRegistry.get_schemas()

        schemas.extend(
            tool.schema
            for tool in self._mcp_tools.values()
        )

        return schemas

    @classmethod
    def execute(
        cls,
        context: ToolContext,
    ) -> ToolResult:

        return cls().execute_instance(context)

    def execute_instance(
        self,
        context: ToolContext,
    ) -> ToolResult:

        from app.config.settings import get_settings

        settings = get_settings()
        if settings.ENABLE_DANGEROUS_TOOL_APPROVAL or settings.ENABLE_INPUT_VALIDATION:
            from security.guard import check_tool_execution
            from security.guard import format_approval_required_result
            from security.guard import set_approval_token

            if context.approval_token:
                set_approval_token(context.approval_token)

            block = check_tool_execution(
                context.tool_name,
                context.arguments,
            )
            if block is not None and not block.allowed:
                if block.needs_approval and block.approval_id:
                    return ToolResult(
                        success=False,
                        content=format_approval_required_result(
                            block.approval_id,
                            context.tool_name,
                        ),
                    )
                return ToolResult(
                    success=False,
                    content=f"Security blocked: {block.reason}",
                )

        if context.tool_name in self._mcp_tools:

            tool = self._mcp_tools[context.tool_name]

            if self._tracer is not None:

                server_name = getattr(
                    tool,
                    "server_name",
                    "unknown",
                )

                mcp_tool_name = getattr(
                    tool,
                    "mcp_tool_name",
                    context.tool_name,
                )

                self._tracer.on_mcp_tool_call(
                    server_name=server_name,
                    tool_name=mcp_tool_name,
                    arguments=context.arguments,
                )

            return tool.execute(context)

        tool = ToolFactory.get(
            context.tool_name
        )

        return tool.execute(
            context
        )

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        return self.execute_instance(context)
