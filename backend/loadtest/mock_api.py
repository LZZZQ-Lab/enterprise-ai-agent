"""Lightweight mock API for Locust stress tests without live LLM."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI

app = FastAPI(title="Stress Test Mock API", version="8.4")

_DELAY_MS = float(__import__("os").getenv("MOCK_API_DELAY_MS", "15"))


def _delay() -> None:
    if _DELAY_MS > 0:
        time.sleep(_DELAY_MS / 1000.0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/chat")
def chat(body: dict) -> dict:
    _delay()
    return {
        "success": True,
        "model": "mock-chat",
        "answer": f"mock reply to: {(body.get('message') or '')[:40]}",
    }


@app.post("/api/v1/dashboard/projects")
def create_project(body: dict) -> dict:
    _delay()
    project_id = f"p-{uuid.uuid4().hex[:8]}"
    return {
        "session_id": f"s-{uuid.uuid4().hex[:8]}",
        "project_id": project_id,
        "name": body.get("project_name") or "stress-demo",
        "requirement": body.get("requirement") or "demo",
        "status": "running",
    }


@app.get("/api/v1/dashboard/workflow/{project_id}")
def workflow_status(project_id: str) -> dict:
    _delay()
    return {
        "project_id": project_id,
        "status": "running",
        "nodes": [{"id": "pm", "status": "done"}, {"id": "developer", "status": "running"}],
    }


@app.post("/api/v1/inference/chat/completions")
def inference_chat(body: dict) -> dict:
    _delay()
    messages = body.get("messages") or []
    content = "mock inference"
    if messages:
        content = f"mock: {messages[-1].get('content', '')[:32]}"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": body.get("model") or "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20},
        "gateway": {"backend": "mock", "duration_ms": _DELAY_MS},
    }


@app.get("/api/v1/inference/stats")
def inference_stats() -> dict:
    return {"total_requests": 0, "total_tokens": 0, "by_backend": {}}
