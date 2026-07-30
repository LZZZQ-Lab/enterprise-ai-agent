"""Task 4.6 structured logging tests."""

from __future__ import annotations

import json
import time

from app.logging.chain import build_agent_chain
from app.logging.context import set_request_id
from app.logging.trace_exporter import StructuredTraceExporter
from app.observability.types import LLMEvent
from app.observability.types import PromptEvent
from app.observability.types import ToolEvent
from app.observability.types import Trace
from app.observability.types import TraceEventType


def test_build_agent_chain_includes_request_and_tokens() -> None:

    trace = Trace(
        trace_id="trace-abc",
        session_id="sess-1",
        start_time=time.time(),
        end_time=time.time() + 1.0,
        duration=1.0,
        metadata={"request_id": "req-123"},
        events=[
            PromptEvent(
                event_type=TraceEventType.PROMPT,
                timestamp=time.time(),
                message_count=2,
                prompt_length=100,
                token_count=25,
            ),
            LLMEvent(
                event_type=TraceEventType.LLM,
                timestamp=time.time(),
                model="test-model",
                duration_ms=120.0,
                prompt_tokens=25,
                completion_tokens=40,
            ),
            ToolEvent(
                event_type=TraceEventType.TOOL,
                timestamp=time.time(),
                tool_name="search_knowledge",
                success=True,
                duration_ms=15.0,
            ),
        ],
    )

    chain = build_agent_chain(trace)

    assert chain["request_id"] == "req-123"
    assert chain["summary"]["llm_call_count"] == 1
    assert chain["summary"]["tool_call_count"] == 1
    assert chain["summary"]["total_tokens"] == 65
    assert len(chain["steps"]) == 3


def test_structured_exporter_writes_artifact(
    tmp_path,
) -> None:

    set_request_id("req-export")

    trace = Trace(
        trace_id="trace-export",
        session_id="sess-x",
        start_time=time.time(),
        duration=0.5,
        events=[
            LLMEvent(
                event_type=TraceEventType.LLM,
                timestamp=time.time(),
                model="m",
                prompt_tokens=1,
                completion_tokens=2,
            ),
        ],
    )

    exporter = StructuredTraceExporter(
        output_dir=tmp_path,
        log_text_summary=False,
    )

    exporter.export(trace)

    path = tmp_path / "trace-export.json"
    assert path.is_file()

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["request_id"] == "req-export"
    assert payload["summary"]["completion_tokens"] == 2
