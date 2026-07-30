"""
Task 4.6：Trace 导出为结构化日志 + JSON 文件。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.logging.chain import build_agent_chain
from app.logging.chain import format_agent_chain_text
from app.logging.context import get_request_id
from app.logging.context import set_trace_id
from app.logging.structured import log_event
from app.observability.exporter import TraceExporter
from app.observability.types import Trace


class StructuredTraceExporter(TraceExporter):
    """
    将 Trace 转为结构化 JSON 日志，并可选落盘。
    """

    def __init__(
        self,
        output_dir: str | Path = "artifacts/agent_traces",
        *,
        log_text_summary: bool = True,
    ) -> None:

        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._log_text_summary = log_text_summary

    def export(self, trace: Trace) -> None:

        set_trace_id(trace.trace_id)

        chain = build_agent_chain(
            trace,
            request_id=get_request_id(),
        )

        path = self._output_dir / f"{trace.trace_id}.json"

        path.write_text(
            json.dumps(chain, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        log_event(
            "agent_chain_complete",
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            request_id=chain.get("request_id"),
            summary=chain.get("summary"),
            artifact=str(path),
        )

        if self._log_text_summary:

            log_event(
                "agent_chain_detail",
                message=format_agent_chain_text(chain),
            )
