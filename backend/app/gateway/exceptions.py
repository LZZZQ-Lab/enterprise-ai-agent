"""
Inference Gateway 统一异常。
"""

from __future__ import annotations

from typing import Any


class GatewayError(Exception):
    """网关基础异常。"""

    def __init__(
        self,
        message: str,
        *,
        code: str = "gateway_error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class GatewayConnectionError(GatewayError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message,
            code="gateway_connection_error",
            status_code=503,
            **kwargs,
        )


class GatewayRateLimitError(GatewayError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message,
            code="gateway_rate_limit",
            status_code=429,
            **kwargs,
        )


class GatewayBackendError(GatewayError):
    def __init__(
        self,
        message: str,
        *,
        backend: str = "",
        status_code: int = 502,
        **kwargs: Any,
    ) -> None:
        details = dict(kwargs.pop("details", {}) or {})
        if backend:
            details["backend"] = backend
        super().__init__(
            message,
            code="gateway_backend_error",
            status_code=status_code,
            details=details,
            **kwargs,
        )


class GatewayValidationError(GatewayError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message,
            code="gateway_validation_error",
            status_code=400,
            **kwargs,
        )
