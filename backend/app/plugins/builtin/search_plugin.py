"""
Search Tool Plugin — 企业搜索扩展（示例）。
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.plugins.base import AgentPlugin
from app.plugins.base import PluginMetadata
from app.plugins.base import PluginKind
from app.plugins.base import ToolPlugin
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

_SEARCH_INDEX = {
    "onboarding": "Employee onboarding handbook v3",
    "api auth": "Internal API uses OAuth2 client credentials",
    "runbook": "Incident runbook: page SRE, collect logs, rollback",
}


class SearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "enterprise_search"

    @property
    def description(self) -> str:
        return "Search enterprise knowledge index (plugin demo)."

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
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max hits",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def execute(self, context: ToolContext) -> ToolResult:
        query = str(context.arguments.get("query", "")).strip().lower()
        limit = int(context.arguments.get("limit", 3))

        hits = [
            f"- {key}: {value}"
            for key, value in _SEARCH_INDEX.items()
            if query in key or query in value.lower()
        ][: max(1, limit)]

        if not hits:
            hits = [f"(no hits for {query!r})"]

        return ToolResult(success=True, content="\n".join(hits))


class SearchAssistantAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "search_assistant"

    def get_capabilities(self) -> list[str]:
        return ["search", "plugin"]

    def execute(self, context: AgentContext) -> AgentResult:
        tool = SearchTool()
        result = tool.execute(
            ToolContext(
                tool_name=tool.name,
                arguments={"query": context.user_message, "limit": 5},
            )
        )
        return AgentResult(
            success=result.success,
            model="plugin-search",
            content=result.content,
        )


class SearchToolPlugin(ToolPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="enterprise.search.tool",
            name="Search Plugin",
            version="1.0.0",
            kind=PluginKind.TOOL,
            description="Enterprise search tool",
            tags=("search", "knowledge"),
        )

    def tool(self) -> BaseTool:
        return SearchTool()


class SearchAgentPlugin(AgentPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="enterprise.search.agent",
            name="Search Agent Plugin",
            version="1.0.0",
            kind=PluginKind.AGENT,
            description="Agent wrapper over search tool",
            tags=("search", "agent"),
        )

    def agent_name(self) -> str:
        return "search_assistant"

    def agent_class(self):
        return SearchAssistantAgent


class SearchPlugin(ToolPlugin):
    """
    组合导出：默认注册 Tool；Demo 可同时激活 Agent 插件类。
    """

    @property
    def metadata(self) -> PluginMetadata:
        return SearchToolPlugin().metadata

    def tool(self) -> BaseTool:
        return SearchTool()


PLUGIN = SearchPlugin()
