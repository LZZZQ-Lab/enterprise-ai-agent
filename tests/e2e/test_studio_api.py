"""Agent Studio API tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.main import app
from app.plugins.loader import PluginLoader
from app.prompts.repository import PROMPT_DEVELOPER
from app.studio.service import default_studio_service
from app.workflow.examples.team_human_approval_workflow import (
    build_team_human_approval_workflow,
)
from app.workflow.executor import WorkflowExecutor
from app.workflow.registry import WorkflowRegistry


class _MockRuntime:
    def run(
        self,
        task: AgentTask,
        *,
        config=None,
        **kwargs: Any,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            model="mock",
            content=f"ok-{task.agent_name}",
        )


def _setup_studio_run() -> str:
    workflow_reg = WorkflowRegistry()
    graph = build_team_human_approval_workflow()
    workflow_reg.register(graph)

    executor = WorkflowExecutor(runtime=_MockRuntime())
    default_studio_service.bind_workflow_executor(executor)

    from app.workflow.registry import default_workflow_registry

    default_workflow_registry.register(graph, overwrite=True)

    PluginLoader().load_and_activate_builtin()

    result = executor.run(
        graph,
        session_id="studio-test",
        user_message="demo task",
    )

    default_studio_service.store.touch_session(
        "studio-test",
        run_id=result.run_id,
    )

    return result.run_id


def test_studio_get_endpoints() -> None:
    run_id = _setup_studio_run()
    client = TestClient(app)

    wf = client.get(
        "/workflow",
        params={"workflow_id": "team_with_human_approval_v1", "run_id": run_id},
    )
    assert wf.status_code == 200
    assert wf.json()["workflow_id"] == "team_with_human_approval_v1"

    prompt = client.get(
        "/prompt",
        params={"prompt_id": PROMPT_DEVELOPER, "version": "1.0.0"},
    )
    assert prompt.status_code == 200
    assert "Developer" in prompt.json()["content"]

    memory = client.get(
        "/memory",
        params={"session_id": "studio-test"},
    )
    assert memory.status_code == 200

    tools = client.get("/tools")
    assert tools.status_code == 200
    assert any(t["name"] == "enterprise_search" for t in tools.json()["tools"])

    status = client.get("/agent/status", params={"run_id": run_id})
    assert status.status_code == 200
    assert status.json()["run_id"] == run_id


def test_studio_update_prompt_and_rerun() -> None:
    run_id = _setup_studio_run()
    client = TestClient(app)

    updated = client.post(
        "/prompt",
        json={
            "prompt_id": PROMPT_DEVELOPER,
            "version": "1.0.0",
            "content": "Studio custom developer prompt {dev_instruction}",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["overridden"] is True

    rerun = client.post(
        "/workflow/rerun",
        json={"run_id": run_id, "node_id": "developer"},
    )
    assert rerun.status_code == 200
    assert "developer" in rerun.json()["node_results"]
