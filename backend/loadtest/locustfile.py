"""Task 8.4 Locust stress test — API / Agent Workflow / Inference Gateway."""

from __future__ import annotations

import os
import uuid

from locust import HttpUser
from locust import between
from locust import task

# Fixed-request shape (1000 requests scenario)
if os.getenv("LOCUST_SCENARIO") == "1000_requests":
    from loadtest.shapes import StopAfterRequests  # noqa: F401


class ApiUser(HttpUser):
    """Platform API: health + chat."""

    weight = 3
    wait_time = between(0.1, 0.5)

    @task(3)
    def health(self) -> None:
        self.client.get("/health", name="API GET /health")

    @task(1)
    def chat(self) -> None:
        self.client.post(
            "/api/v1/chat",
            json={
                "session_id": f"locust-{uuid.uuid4().hex[:12]}",
                "message": "请用一句话介绍企业级 AI 助手平台。",
            },
            name="API POST /api/v1/chat",
            timeout=120,
        )


class AgentWorkflowUser(HttpUser):
    """Agent Workflow: create project + poll workflow status."""

    weight = 2
    wait_time = between(0.2, 0.8)

    def on_start(self) -> None:
        self._project_id: str | None = None

    @task(1)
    def create_project(self) -> None:
        with self.client.post(
            "/api/v1/dashboard/projects",
            json={
                "requirement": "开发一个用户管理系统",
                "project_name": f"locust-{uuid.uuid4().hex[:8]}",
                "user_id": "locust",
            },
            name="Workflow POST /api/v1/dashboard/projects",
            timeout=180,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                body = response.json()
                self._project_id = body.get("project_id")
                response.success()
            else:
                response.failure(f"status {response.status_code}")

    @task(2)
    def workflow_status(self) -> None:
        project_id = self._project_id or "demo-project"
        self.client.get(
            f"/api/v1/dashboard/workflow/{project_id}",
            name="Workflow GET /api/v1/dashboard/workflow/{id}",
            timeout=60,
        )


class InferenceGatewayUser(HttpUser):
    """Inference Gateway: chat completions + stats."""

    weight = 2
    wait_time = between(0.1, 0.4)

    @task(3)
    def chat_completions(self) -> None:
        self.client.post(
            "/api/v1/inference/chat/completions",
            json={
                "model": os.getenv("STRESS_INFERENCE_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": "hi from locust stress test"}],
                "temperature": 0.7,
                "max_tokens": 64,
                "stream": False,
            },
            name="Gateway POST /api/v1/inference/chat/completions",
            timeout=120,
        )

    @task(1)
    def stats(self) -> None:
        self.client.get(
            "/api/v1/inference/stats",
            name="Gateway GET /api/v1/inference/stats",
            timeout=30,
        )
