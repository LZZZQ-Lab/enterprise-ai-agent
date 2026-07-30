"""Task 8.7: structured logging engine with optional file sink."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from observability.logging.context import get_log_context
from observability.logging.formatter import JsonLogFormatter

STRUCTURED_LOGGER_NAME = "enterprise.agent.structured"
SERVICE_NAME = "enterprise-ai-agent"

_configured = False
_log_store: list[dict[str, Any]] = []


def get_log_store() -> list[dict[str, Any]]:
    """内存日志存储（Demo / 单测查询用）。"""
    return _log_store


def clear_log_store() -> None:
    _log_store.clear()


def get_structured_logger() -> logging.Logger:
    return logging.getLogger(STRUCTURED_LOGGER_NAME)


def configure_structured_logging(
    *,
    level: int = logging.INFO,
    log_file: str | Path | None = None,
    service_name: str = SERVICE_NAME,
    enable_memory_store: bool = True,
) -> logging.Logger:
    """配置 stdout JSON 行输出；可选写入文件供 ELK/Loki 采集。"""
    global _configured

    log = get_structured_logger()
    if _configured and log.handlers:
        return log

    log.setLevel(level)
    log.propagate = False
    formatter = JsonLogFormatter(service_name=service_name)

    stdout = logging.StreamHandler()
    stdout.setFormatter(formatter)
    log.addHandler(stdout)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

    _configured = True
    return log


def _level_name(level: int) -> str:
    return logging.getLevelName(level)


def log_event(
    event: str,
    *,
    level: int = logging.INFO,
    message: str | None = None,
    store: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    """
    输出单行 JSON 结构化日志。

    自动合并 contextvars：request_id / user_id / project_id / agent_id /
    workflow_id / token_usage / latency_ms。
    """
    import json

    payload: dict[str, Any] = {
        "event": event,
        **get_log_context(),
        **fields,
    }
    if message:
        payload["message"] = message

    log = get_structured_logger()
    if not log.handlers:
        configure_structured_logging()

    record_dict = {
        "@timestamp": payload.get("@timestamp"),
        "level": _level_name(level),
        "event": event,
        "service": SERVICE_NAME,
        **payload,
    }

    if store:
        _log_store.append(record_dict)

    log.log(level, json.dumps(payload, ensure_ascii=False, default=str))
    return record_dict


def log_http_request(
    *,
    phase: str,
    method: str,
    path: str,
    status_code: int | None = None,
    latency_ms: float | None = None,
) -> None:
    fields: dict[str, Any] = {"method": method, "path": path, "phase": phase}
    if status_code is not None:
        fields["status_code"] = status_code
    if latency_ms is not None:
        fields["latency_ms"] = round(latency_ms, 3)
    log_event(f"http_{phase}", **fields)


def log_agent_execution(
    *,
    agent_id: str,
    workflow_id: str | None = None,
    project_id: str | None = None,
    token_usage: dict[str, int] | None = None,
    latency_ms: float | None = None,
    model: str | None = None,
    success: bool = True,
) -> None:
    fields: dict[str, Any] = {
        "agent_id": agent_id,
        "success": success,
    }
    if workflow_id:
        fields["workflow_id"] = workflow_id
    if project_id:
        fields["project_id"] = project_id
    if token_usage:
        fields["token_usage"] = token_usage
    if latency_ms is not None:
        fields["latency_ms"] = round(latency_ms, 3)
    if model:
        fields["model"] = model
    log_event("agent_execution", **fields)
