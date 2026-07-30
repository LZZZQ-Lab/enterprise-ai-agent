"""Task 6.6 Plugin System tests."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry
from app.tools.registry import ToolRegistry
from app.tools.types import ToolContext
from app.workflow.registry import WorkflowRegistry


@pytest.fixture()
def isolated_registries() -> tuple[
    AgentRegistry,
    WorkflowRegistry,
    PluginRegistry,
]:
    return AgentRegistry(), WorkflowRegistry(), PluginRegistry()


def test_load_builtin_plugins_without_core_changes(
    isolated_registries: tuple[
        AgentRegistry,
        WorkflowRegistry,
        PluginRegistry,
    ],
) -> None:
    agent_reg, workflow_reg, plugin_reg = isolated_registries

    loader = PluginLoader(
        plugin_registry=plugin_reg,
        agent_registry=agent_reg,
        workflow_registry=workflow_reg,
    )

    activated = loader.load_and_activate_builtin()

    assert "enterprise.search.tool" in activated
    assert "enterprise.git" in activated
    assert "enterprise.database" in activated
    assert "enterprise.search.workflow" in activated

    ToolRegistry.get("enterprise_search")
    ToolRegistry.get("enterprise_git")
    ToolRegistry.get("enterprise_database")

    assert agent_reg.has("search_assistant")
    workflow_reg.get("plugin_search_v1")


def test_tool_plugins_execute(isolated_registries) -> None:
    agent_reg, workflow_reg, plugin_reg = isolated_registries
    loader = PluginLoader(
        plugin_registry=plugin_reg,
        agent_registry=agent_reg,
        workflow_registry=workflow_reg,
    )
    loader.load_and_activate_builtin()

    search = ToolRegistry.get("enterprise_search")
    git = ToolRegistry.get("enterprise_git")
    db = ToolRegistry.get("enterprise_database")

    assert "onboarding" in search.execute(
        ToolContext(tool_name=search.name, arguments={"query": "onboarding"})
    ).content

    assert "branch" in git.execute(
        ToolContext(tool_name=git.name, arguments={"action": "status"})
    ).content.lower()

    ok = db.execute(
        ToolContext(
            tool_name=db.name,
            arguments={"sql": "select * from users"},
        )
    )
    assert ok.success

    bad = db.execute(
        ToolContext(
            tool_name=db.name,
            arguments={"sql": "delete from users"},
        )
    )
    assert not bad.success


def test_search_agent_via_runtime(isolated_registries) -> None:
    agent_reg, workflow_reg, plugin_reg = isolated_registries

    loader = PluginLoader(
        plugin_registry=plugin_reg,
        agent_registry=agent_reg,
        workflow_registry=workflow_reg,
    )
    loader.load_and_activate_builtin()

    from app.scheduler.scheduler import AgentScheduler

    scheduler = AgentScheduler(worker_count=1, auto_start=True)
    runtime = AgentRuntime(registry=agent_reg, scheduler=scheduler)
    scheduler.set_executor(runtime.execute_task)

    result = runtime.run(
        AgentTask(
            session_id="plugin",
            user_message="api auth",
            agent_name="search_assistant",
        )
    )

    assert result.success
    assert "OAuth2" in result.content or "api auth" in result.content.lower()
