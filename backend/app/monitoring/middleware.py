"""HTTP 请求延迟与 QPS 统计（写入 infra_metrics）。"""

from __future__ import annotations

import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.monitoring.metrics import infra_metrics


_SKIP_PATHS = frozenset(
    {
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }
)

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def normalize_route(path: str) -> str:
    """
    降低 Prometheus 标签基数（UUID / 数字 ID →占位符）。
    """

    if path in _SKIP_PATHS or path == "/":

        return path

    normalized = _UUID_RE.sub("{id}", path)
    normalized = re.sub(r"/\d+(?=/)", "/{id}", normalized)
    normalized = re.sub(r"/\d+$", "/{id}", normalized)

    return normalized


class InfraMetricsMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的耗时与状态码。"""

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:

        path = request.url.path

        if path in _SKIP_PATHS:

            return await call_next(request)

        start = time.perf_counter()
        status_code = 500

        try:

            response = await call_next(request)
            status_code = response.status_code

            return response

        finally:

            duration = time.perf_counter() - start
            route = normalize_route(path)

            infra_metrics.record_http_request(
                method=request.method,
                route=route,
                status_code=status_code,
                duration_sec=duration,
            )
