"""
Search Workflow Plugin — Workflow 扩展示例。
"""

from __future__ import annotations

from app.plugins.base import PluginKind
from app.plugins.base import PluginMetadata
from app.plugins.base import WorkflowPlugin
from app.workflow.graph import WorkflowGraph
from app.workflow.node import WorkflowNode


def build_search_plugin_workflow() -> WorkflowGraph:
    graph = WorkflowGraph(
        id="plugin_search_v1",
        name="Plugin Search Workflow",
        description="Tool search → summarize (demo)",
        entry_node_id="search",
    )

    graph.add_node(
        WorkflowNode.tool(
            node_id="search",
            tool_name="enterprise_search",
            arguments={"query": "{user_message}", "limit": 3},
            name="Enterprise Search",
        )
    )

    graph.add_node(
        WorkflowNode.tool(
            node_id="notify",
            tool_name="enterprise_git",
            arguments={"action": "status", "path": "workspace"},
            name="Git Status",
        )
    )

    graph.add_edge("search", "notify")
    return graph


class SearchWorkflowPlugin(WorkflowPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="enterprise.search.workflow",
            name="Search Workflow Plugin",
            version="1.0.0",
            kind=PluginKind.WORKFLOW,
            description="Registers plugin_search_v1 workflow",
            tags=("workflow", "search"),
        )

    def workflow(self) -> WorkflowGraph:
        return build_search_plugin_workflow()


PLUGIN = SearchWorkflowPlugin()
