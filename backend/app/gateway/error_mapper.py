"""
将底层异常映射为 Gateway 统一异常。
"""

from __future__ import annotations

from openai import APIConnectionError
from openai import APIStatusError
from openai import APITimeoutError
from openai import RateLimitError

from app.gateway.exceptions import GatewayBackendError
from app.gateway.exceptions import GatewayConnectionError
from app.gateway.exceptions import GatewayError
from app.gateway.exceptions import GatewayRateLimitError
from app.gateway.types import InferenceBackendKind


def translate_exception(
    exc: Exception,
    *,
    backend: InferenceBackendKind,
) -> GatewayError:
    if isinstance(exc, GatewayError):
        return exc

    if isinstance(exc, RateLimitError):
        return GatewayRateLimitError(
            str(exc),
            details={"backend": backend.value},
        )

    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return GatewayConnectionError(
            str(exc),
            details={"backend": backend.value},
        )

    if isinstance(exc, APIStatusError):
        status = int(getattr(exc, "status_code", 502) or 502)
        return GatewayBackendError(
            str(exc),
            backend=backend.value,
            status_code=status,
        )

    return GatewayBackendError(
        str(exc),
        backend=backend.value,
        status_code=500,
    )
