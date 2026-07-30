"""Task 8.6: API authentication, secret management, permissions."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response

PUBLIC_PATHS = frozenset(
    {
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }
)

PUBLIC_PREFIXES = ("/docs/",)


class Role(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


@dataclass(frozen=True)
class SecurityContext:
    user_id: str
    role: Role
    token_id: str


_security_ctx: ContextVar[SecurityContext | None] = ContextVar(
    "security_context",
    default=None,
)


def set_security_context(ctx: SecurityContext | None) -> None:
    _security_ctx.set(ctx)


def get_security_context() -> SecurityContext | None:
    return _security_ctx.get()


def get_current_user_id() -> str | None:
    ctx = get_security_context()
    return ctx.user_id if ctx else None


def get_current_role() -> Role | None:
    ctx = get_security_context()
    return ctx.role if ctx else None


class SecretManager:
    """从环境变量安全读取密钥，日志中不暴露明文。"""

    _SENSITIVE_KEYS = frozenset(
        {
            "API_KEY",
            "OPENAI_API_KEY",
            "VLLM_API_KEY",
            "SGLANG_API_KEY",
            "TGI_API_KEY",
            "API_AUTH_SECRET",
        }
    )

    @staticmethod
    def get(name: str, default: str = "") -> str:
        return os.getenv(name, default)

    @staticmethod
    def mask(value: str, visible: int = 4) -> str:
        if not value:
            return "(empty)"
        if len(value) <= visible * 2:
            return "*" * len(value)
        return f"{value[:visible]}...{value[-visible:]}"

    @classmethod
    def safe_repr(cls, name: str, value: str) -> str:
        if name.upper() in cls._SENSITIVE_KEYS or "KEY" in name.upper() or "SECRET" in name.upper():
            return cls.mask(value)
        return value


def parse_auth_tokens(raw: str) -> dict[str, tuple[str, Role]]:
    """
    解析 API_AUTH_TOKENS。

    格式：token:role[:user_id],token2:role2
    例：admin-secret:admin:alice,dev-secret:developer:bob
    """
    mapping: dict[str, tuple[str, Role]] = {}
    if not raw.strip():
        return mapping

    for part in raw.split(","):
        piece = part.strip()
        if not piece:
            continue
        fields = piece.split(":")
        if len(fields) < 2:
            continue
        token = fields[0].strip()
        role_str = fields[1].strip().lower()
        user_id = fields[2].strip() if len(fields) > 2 else role_str
        try:
            role = Role(role_str)
        except ValueError:
            role = Role.VIEWER
        mapping[token] = (user_id, role)
    return mapping


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key.strip()
    return None


def _constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def authenticate_token(
    token: str | None,
    token_map: dict[str, tuple[str, Role]],
) -> SecurityContext | None:
    if not token or not token_map:
        return None
    for known, (user_id, role) in token_map.items():
        if _constant_time_equal(token, known):
            token_id = hashlib.sha256(known.encode("utf-8")).hexdigest()[:12]
            return SecurityContext(user_id=user_id, role=role, token_id=token_id)
    return None


class PermissionChecker:
    """基于角色的权限检查。"""

    _ROLE_RANK = {
        Role.VIEWER: 1,
        Role.DEVELOPER: 2,
        Role.ADMIN: 3,
    }

    _ENDPOINT_PERMISSIONS: dict[str, Role] = {
        "chat": Role.VIEWER,
        "knowledge": Role.VIEWER,
        "inference": Role.DEVELOPER,
        "dashboard": Role.DEVELOPER,
        "security_approve": Role.ADMIN,
        "dangerous_tool": Role.ADMIN,
    }

    @classmethod
    def role_at_least(cls, role: Role, minimum: Role) -> bool:
        return cls._ROLE_RANK.get(role, 0) >= cls._ROLE_RANK.get(minimum, 0)

    @classmethod
    def check(cls, permission: str, role: Role | None) -> bool:
        if role is None:
            return False
        required = cls._ENDPOINT_PERMISSIONS.get(permission, Role.ADMIN)
        return cls.role_at_least(role, required)

    @classmethod
    def require(cls, permission: str) -> None:
        ctx = get_security_context()
        role = ctx.role if ctx else None
        if not cls.check(permission, role):
            raise PermissionError(
                f"Permission denied: {permission} requires "
                f"{cls._ENDPOINT_PERMISSIONS.get(permission, Role.ADMIN).value}"
            )


def create_auth_middleware(
    *,
    enabled: bool,
    token_map: dict[str, tuple[str, Role]],
) -> type[BaseHTTPMiddleware]:
    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            path = request.url.path
            if not enabled:
                return await call_next(request)

            if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
                return await call_next(request)

            token = _extract_bearer_token(request)
            ctx = authenticate_token(token, token_map)
            if ctx is None:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid or missing API token",
                        }
                    },
                )

            set_security_context(ctx)
            try:
                return await call_next(request)
            finally:
                set_security_context(None)

    return AuthMiddleware


def resolve_api_auth_settings() -> tuple[bool, dict[str, tuple[str, Role]]]:
    from app.config.settings import get_settings

    settings = get_settings()
    enabled = getattr(settings, "ENABLE_API_AUTH", False)
    raw = getattr(settings, "API_AUTH_TOKENS", "")
    return enabled, parse_auth_tokens(raw)
