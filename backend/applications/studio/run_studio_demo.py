"""
Task 6.8 Agent Studio Demo。

启动 API 后可在 /docs 调试；本脚本用 TestClient 本地演示。

运行:
    cd backend
    python -m applications.studio.run_studio_demo
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.main import app
from app.memory.memory_manager import get_default_enterprise_memory_manager
from app.plugins.loader import PluginLoader
from app.prompts.repository import PROMPT_DEVELOPER
from app.studio.service import default_studio_service
from app.workflow.examples.team_human_approval_workflow import (
    build_team_human_approval_workflow,
)
from app.workflow.executor import WorkflowExecutor
from app.workflow.registry import default_workflow_registry


class DemoRuntime:
    def run(
        self,
        task: AgentTask,
        *,
        config=None,
        **kwargs: Any,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            model="studio-demo",
            content=f"[{task.agent_name}] {task.user_message[:40]}",
        )


def main() -> None:
    print("Agent Studio Demo (Task 6.8)\n")

    graph = build_team_human_approval_workflow()
    default_workflow_registry.register(graph, overwrite=True)
    PluginLoader().load_and_activate_builtin()

    executor = WorkflowExecutor(runtime=DemoRuntime())
    default_studio_service.bind_workflow_executor(executor)

    session_id = "studio-demo"
    memory = get_default_enterprise_memory_manager()
    memory.write_project(
        session_id,
        "task_list",
        "1. Build login API",
        agent_name="manager",
    )

    run = executor.run(
        graph,
        session_id=session_id,
        user_message="Implement auth module",
    )
    default_studio_service.store.touch_session(
        session_id,
        run_id=run.run_id,
        project_id=session_id,
    )

    client = TestClient(app)

    print("GET /workflow")
    print(client.get("/workflow", params={"run_id": run.run_id}).json()["status"])

    print("\nGET /prompt")
    prompt = client.get(
        "/prompt",
        params={"prompt_id": PROMPT_DEVELOPER},
    ).json()
    print(f"  version={prompt['version']} role={prompt['role']}")

    print("\nGET /memory")
    mem = client.get("/memory", params={"session_id": session_id}).json()
    print(f"  project keys: {list(mem['project_memory'].keys())}")

    print("\nGET /tools (count)", len(client.get("/tools").json()["tools"]))

    print("\nGET /agent/status")
    status = client.get("/agent/status", params={"run_id": run.run_id}).json()
    print(f"  workflow={status['workflow_id']} pending={status['pending_node_id']}")

    print("\nPOST /prompt (override)")
    client.post(
        "/prompt",
        json={
            "prompt_id": PROMPT_DEVELOPER,
            "version": "1.0.0",
            "content": "Studio: ship secure code.\n{dev_instruction}",
        },
    )

    print("POST /workflow/rerun node=developer")
    rerun = client.post(
        "/workflow/rerun",
        json={"run_id": run.run_id, "node_id": "developer"},
    )
    print(f"  status after rerun: {rerun.json()['status']}")

    traces = __import__(
        "app.observability.trace",
        fromlist=["default_trace_registry"],
    ).default_trace_registry.list_session(session_id)

    if traces:
        trace = client.get(
            "/trace",
            params={"trace_id": traces[-1].trace_id},
        ).json()
        print(f"\nGET /trace id={trace['trace_id']} events={len(trace['events'])}")

    print("\nOpen Swagger UI: http://127.0.0.1:8000/docs")
    print("Demo finished.")


if __name__ == "__main__":
    main()
