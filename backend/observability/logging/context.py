"""Task 8.7: extended observability log context (contextvars)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import uuid4

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_project_id: ContextVar[str | None] = ContextVar("project_id", default=None)
_agent_id: ContextVar[str | None] = ContextVar("agent_id", default=None)
_workflow_id: ContextVar[str | None] = ContextVar("workflow_id", default=None)
_token_usage: ContextVar[dict[str, int] | None] = ContextVar("token_usage", default=None)
_latency_ms: ContextVar[float | None] = ContextVar("latency_ms", default=None)


def generate_request_id() -> str:
    return uuid4().hex


def set_request_id(request_id: str | None) -> None:
    _request_id.set(request_id)


def get_request_id() -> str | None:
    return _request_id.get()


def set_trace_id(trace_id: str | None) -> None:
    _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id.get()


def set_session_id(session_id: str | None) -> None:
    _session_id.set(session_id)


def get_session_id() -> str | None:
    return _session_id.get()


def set_user_id(user_id: str | None) -> None:
    _user_id.set(user_id)


def get_user_id() -> str | None:
    return _user_id.get()


def set_project_id(project_id: str | None) -> None:
    _project_id.set(project_id)


def get_project_id() -> str | None:
    return _project_id.get()


def set_agent_id(agent_id: str | None) -> None:
    _agent_id.set(agent_id)


def get_agent_id() -> str | None:
    return _agent_id.get()


def set_workflow_id(workflow_id: str | None) -> None:
    _workflow_id.set(workflow_id)


def get_workflow_id() -> str | None:
    return _workflow_id.get()


def set_token_usage(usage: dict[str, int] | None) -> None:
    _token_usage.set(usage)


def get_token_usage() -> dict[str, int] | None:
    return _token_usage.get()


def set_latency_ms(latency_ms: float | None) -> None:
    _latency_ms.set(latency_ms)


def get_latency_ms() -> float | None:
    return _latency_ms.get()


def bind_user_from_security() -> None:
    """从 security 模块同步 user_id（若已认证）。"""
    try:
        from security.auth import get_current_user_id

        uid = get_current_user_id()
        if uid:
            set_user_id(uid)
    except ImportError:
        return


def get_log_context() -> dict[str, Any]:
    """收集当前上下文中的关联字段（JSON 可序列化）。"""
    context: dict[str, Any] = {}

    for key, getter in (
        ("request_id", get_request_id),
        ("trace_id", get_trace_id),
        ("session_id", get_session_id),
        ("user_id", get_user_id),
        ("project_id", get_project_id),
        ("agent_id", get_agent_id),
        ("workflow_id", get_workflow_id),
    ):
        value = getter()
        if value:
            context[key] = value

    usage = get_token_usage()
    if usage:
        context["token_usage"] = dict(usage)

    latency = get_latency_ms()
    if latency is not None:
        context["latency_ms"] = round(latency, 3)

    return context


def clear_context() -> None:
    _request_id.set(None)
    _trace_id.set(None)
    _session_id.set(None)
    _user_id.set(None)
    _project_id.set(None)
    _agent_id.set(None)
    _workflow_id.set(None)
    _token_usage.set(None)
    _latency_ms.set(None)
