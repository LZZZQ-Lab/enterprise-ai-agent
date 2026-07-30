from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.monitoring.collector import default_collector

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus 指标（GPU / QPS / Latency / Tokens）",
)
def prometheus_metrics() -> PlainTextResponse:
    """
    AI Infra 监控刮取端点。

    - GPU：显存、利用率
    - 服务：http_requests_total、request_duration、llm_tokens_total
    """

    body = default_collector.scrape()

    return PlainTextResponse(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
