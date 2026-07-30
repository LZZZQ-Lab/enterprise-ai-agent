"""
可观测性结构化日志（Task 6.4）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.observability.types import Trace

_log = logging.getLogger("enterprise.observability")


class ObservabilityLogger:
    """
    统一 Observability 日志出口。
    """

    def __init__(self, name: str = "enterprise.observability") -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str, **fields: Any) -> None:
        self._emit(logging.INFO, message, fields)

    def debug(self, message: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, message, fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit(logging.WARNING, message, fields)

    def trace_finished(self, trace: Trace, *, timeline: str = "") -> None:
        payload = {
            "trace_id": trace.trace_id,
            "session_id": trace.session_id,
            "duration_sec": trace.duration,
            "agent_name": trace.metadata.get("agent_name", ""),
            "event_count": len(trace.events),
        }
        self.info("agent trace finished", **payload)

        if timeline:
            self._logger.info(
                "Agent Execution Timeline\n%s",
                timeline,
            )

    def _emit(
        self,
        level: int,
        message: str,
        fields: dict[str, Any],
    ) -> None:
        if fields:
            self._logger.log(
                level,
                "%s | %s",
                message,
                json.dumps(fields, ensure_ascii=False, default=str),
            )
            return

        self._logger.log(level, message)


default_observability_logger = ObservabilityLogger()
