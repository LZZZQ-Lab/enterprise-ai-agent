"""Task 4.5 monitoring 模块测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.monitoring.metrics import InfraMetricsRegistry
from app.monitoring.middleware import normalize_route
from app.monitoring.collector import InfraMetricsCollector


def test_normalize_route_replaces_uuid() -> None:

    path = (
        "/api/v1/dashboard/projects/"
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )

    assert "{id}" in normalize_route(path)


def test_metrics_registry_prometheus_format() -> None:

    registry = InfraMetricsRegistry()

    registry.record_http_request(
        method="POST",
        route="/api/v1/chat",
        status_code=200,
        duration_sec=0.42,
    )

    registry.record_llm_usage(
        model="test-model",
        prompt_tokens=10,
        completion_tokens=20,
        duration_sec=1.0,
    )

    registry.gauge_set(
        "ai_infra_gpu_utilization_percent",
        55.0,
        labels={"gpu": "0"},
    )

    text = registry.render_prometheus()

    assert "ai_infra_http_requests_total" in text
    assert "ai_infra_http_request_duration_seconds_bucket" in text
    assert 'type="prompt"' in text or "prompt" in text
    assert "ai_infra_gpu_utilization_percent" in text


def test_metrics_endpoint() -> None:

    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "ai_infra_gpu_memory_used_mib" in response.text or (
        "# TYPE" in response.text
    )


def test_collector_refresh_gpu_no_crash() -> None:

    collector = InfraMetricsCollector(
        registry=InfraMetricsRegistry(),
    )

    snap = collector.refresh_gpu_gauges()

    assert snap.gpu_index == 0
    assert collector.scrape().startswith("# TYPE")
