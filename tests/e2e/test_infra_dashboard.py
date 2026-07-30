"""Task 7.8 AI Infra Dashboard 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.dashboard.collector import InfraDashboardCollector
from app.gateway.stats import record_token_usage
from app.gateway.stats import reset_token_stats
from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage
from app.main import app
from app.monitoring.metrics import infra_metrics


def test_infra_metrics_summarize_keys() -> None:
    infra_metrics.record_http_request(
        method="GET",
        route="/api/v1/infra/dashboard/overview",
        status_code=200,
        duration_sec=0.05,
    )
    summary = infra_metrics.summarize()
    assert "http_error_rate" in summary
    assert "llm_by_model" in summary
    assert "gpu_devices" in summary


def test_collector_returns_overview() -> None:
    overview = InfraDashboardCollector().collect()
    assert overview.generated_at is not None
    assert isinstance(overview.models, list)
    assert overview.cache.backend in ("memory", "redis")


def test_overview_api_and_demo_page() -> None:
    reset_token_stats()
    record_token_usage(
        backend=InferenceBackendKind.OPENAI,
        model="demo-model",
        usage=TokenUsage(
            prompt_tokens=3,
            completion_tokens=7,
            total_tokens=10,
        ),
    )

    client = TestClient(app)

    overview = client.get("/api/v1/infra/dashboard/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert "models" in body
    assert "http_error_rate" in body
    assert "gateway_tokens" in body
    assert body["gateway_tokens"]["total_tokens"] >= 10
    assert "agents" in body

    demo = client.get("/infra/dashboard/demo")
    assert demo.status_code == 200
    assert "text/html" in demo.headers["content-type"]
    assert "AI Infra Dashboard Demo" in demo.text
    assert "/api/v1/infra/dashboard/overview" in demo.text
