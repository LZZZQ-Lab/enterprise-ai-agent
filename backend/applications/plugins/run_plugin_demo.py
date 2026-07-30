"""
Task 6.6 Plugin Demo。

加载 Search / Git / Database / Workflow 插件并演示注册与调用。

运行:
    cd backend
    python -m applications.plugins.run_plugin_demo
"""

from __future__ import annotations

from typing import Any

from app.agents.registry import AgentRegistry
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry
from app.tools.registry import ToolRegistry
from app.tools.types import ToolResult
from app.workflow.executor import WorkflowExecutor
from app.tools.types import ToolContext
from app.workflow.registry import WorkflowRegistry


class PluginToolExecutor:
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        from app.tools.types import ToolContext

        tool = ToolRegistry.get(tool_name)
        return tool.execute(ToolContext(tool_name=tool_name, arguments=arguments))


def main() -> None:
    print("Enterprise Plugin System Demo (Task 6.6)\n")

    agent_reg = AgentRegistry()
    workflow_reg = WorkflowRegistry()
    plugin_reg = PluginRegistry()

    loader = PluginLoader(
        plugin_registry=plugin_reg,
        agent_registry=agent_reg,
        workflow_registry=workflow_reg,
    )

    activated = loader.load_and_activate_builtin()
    print("Activated plugins:")
    for plugin_id in activated:
        meta = plugin_reg.get(plugin_id).metadata
        print(f"  - {plugin_id} ({meta.kind.value}) v{meta.version}")

    print("\n--- Tool: enterprise_search ---")
    search = ToolRegistry.get("enterprise_search")
    print(
        search.execute(
            ToolContext(tool_name=search.name, arguments={"query": "runbook"})
        ).content
    )

    print("\n--- Tool: enterprise_git ---")
    git = ToolRegistry.get("enterprise_git")
    print(
        git.execute(
            ToolContext(tool_name=git.name, arguments={"action": "status"})
        ).content
    )

    print("\n--- Tool: enterprise_database ---")
    db = ToolRegistry.get("enterprise_database")
    print(
        db.execute(
            ToolContext(
                tool_name=db.name,
                arguments={"sql": "select id, name from projects"},
            )
        ).content
    )

    print("\n--- Workflow: plugin_search_v1 ---")
    graph = workflow_reg.get("plugin_search_v1")
    executor = WorkflowExecutor(tool_executor=PluginToolExecutor())
    wf_result = executor.run(
        graph,
        session_id="plugin-demo",
        user_message="onboarding",
    )
    print(f"Workflow status: {wf_result.status.value}")
    for node_id, node_result in wf_result.node_results.items():
        print(f"  {node_id}: {node_result.output[:80]!r}")

    print("\nDemo finished.")


if __name__ == "__main__":
    main()
