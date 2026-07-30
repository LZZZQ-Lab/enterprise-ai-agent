"""HTTP Request ID 注入 + Task 8.7 结构化字段（latency / user_id）。"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging.context import clear_context
from app.logging.context import generate_request_id
from app.logging.context import set_request_id
from observability.logging.context import bind_user_from_security
from observability.logging.context import set_latency_ms
from observability.logging.logger import log_http_request


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    为每个 HTTP 请求分配 ``request_id``，并写入响应头 ``X-Request-ID``。
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:

        incoming = request.headers.get(self.HEADER_NAME)
        request_id = incoming or generate_request_id()

        set_request_id(request_id)
        bind_user_from_security()

        log_http_request(
            phase="request_start",
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
        except Exception as error:
            latency_ms = (time.perf_counter() - start) * 1000.0
            set_latency_ms(latency_ms)
            log_http_request(
                phase="request_error",
                method=request.method,
                path=request.url.path,
                latency_ms=latency_ms,
            )
            from observability.logging.logger import log_event

            log_event(
                "http_request_error",
                method=request.method,
                path=request.url.path,
                error=str(error),
                latency_ms=latency_ms,
                level=logging.ERROR,
            )
            clear_context()
            raise

        latency_ms = (time.perf_counter() - start) * 1000.0
        set_latency_ms(latency_ms)
        log_http_request(
            phase="request_end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )

        clear_context()
        response.headers[self.HEADER_NAME] = request_id
        return response
