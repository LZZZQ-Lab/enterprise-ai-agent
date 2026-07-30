"""
Gateway 统一结构化日志。
"""

from __future__ import annotations

from typing import Any

from app.core.logger import logger
from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage


def log_gateway_request(
    *,
    request_id: str,
    backend: InferenceBackendKind,
    model: str,
    message_count: int,
    use_tools: bool,
) -> None:
    logger.info(
        "gateway.request id=%s backend=%s model=%s messages=%d tools=%s",
        request_id,
        backend.value,
        model,
        message_count,
        use_tools,
        extra={
            "gateway_event": "request",
            "request_id": request_id,
            "backend": backend.value,
            "model": model,
        },
    )


def log_gateway_response(
    *,
    request_id: str,
    backend: InferenceBackendKind,
    model: str,
    duration_ms: float,
    usage: TokenUsage,
    success: bool = True,
    error_code: str | None = None,
) -> None:
    logger.info(
        (
            "gateway.response id=%s backend=%s model=%s "
            "duration_ms=%.1f tokens=%d success=%s"
        ),
        request_id,
        backend.value,
        model,
        duration_ms,
        usage.total_tokens,
        success,
        extra={
            "gateway_event": "response",
            "request_id": request_id,
            "backend": backend.value,
            "model": model,
            "duration_ms": duration_ms,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "success": success,
            "error_code": error_code,
        },
    )


def log_gateway_error(
    request_id: str,
    exc: Exception,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {"gateway_event": "error", "request_id": request_id}
    if extra:
        payload.update(extra)
    logger.error(
        "gateway.error id=%s type=%s msg=%s",
        request_id,
        type(exc).__name__,
        str(exc),
        extra=payload,
    )
