"""Task 8.7: JSON log formatter compatible with ELK / Loki / Grafana."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from datetime import timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """
    单行 JSON 日志，便于 ELK（Elasticsearch）与 Loki（labels + json）采集。

    字段约定：
    - @timestamp: ISO8601 UTC
    - level: 日志级别
    - event: 事件名（Loki 可用作 label）
    - service: 服务名
    - message: 人类可读摘要（可选）
    """

    def __init__(
        self,
        *,
        service_name: str = "enterprise-ai-agent",
    ) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any]

        if isinstance(record.msg, dict):
            payload = dict(record.msg)
        elif isinstance(record.msg, str) and record.msg.startswith("{"):
            try:
                payload = json.loads(record.msg)
            except json.JSONDecodeError:
                payload = {"message": record.getMessage()}
        else:
            payload = {"message": record.getMessage()}

        payload.setdefault(
            "@timestamp",
            datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        )
        payload.setdefault("level", record.levelname)
        payload.setdefault("service", self.service_name)
        payload.setdefault("logger", record.name)

        if record.exc_info and record.exc_info[1]:
            payload["error"] = str(record.exc_info[1])

        return json.dumps(payload, ensure_ascii=False, default=str)


def format_log_event(
    event: str,
    *,
    level: str = "INFO",
    service_name: str = "enterprise-ai-agent",
    message: str | None = None,
    **fields: Any,
) -> str:
    """构建单行 JSON 字符串（不写入 handler）。"""
    payload: dict[str, Any] = {
        "@timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": level,
        "event": event,
        "service": service_name,
        **fields,
    }
    if message:
        payload["message"] = message
    return json.dumps(payload, ensure_ascii=False, default=str)
