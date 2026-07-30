"""Task 8.7 structured logging tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from observability.logging.context import clear_context
from observability.logging.context import get_log_context
from observability.logging.context import set_agent_id
from observability.logging.context import set_project_id
from observability.logging.context import set_request_id
from observability.logging.context import set_token_usage
from observability.logging.context import set_user_id
from observability.logging.context import set_workflow_id
from observability.logging.formatter import format_log_event
from observability.logging.logger import clear_log_store
from observability.logging.logger import configure_structured_logging
from observability.logging.logger import get_log_store
from observability.logging.logger import log_event
from observability.logging.query import LogQuery
from observability.logging.query import LogQueryEngine


def test_log_context_includes_all_ids() -> None:
    clear_context()
    set_request_id("req-1")
    set_user_id("u1")
    set_project_id("p1")
    set_agent_id("chat")
    set_workflow_id("wf1")
    set_token_usage({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

    ctx = get_log_context()
    assert ctx["request_id"] == "req-1"
    assert ctx["user_id"] == "u1"
    assert ctx["project_id"] == "p1"
    assert ctx["agent_id"] == "chat"
    assert ctx["workflow_id"] == "wf1"
    assert ctx["token_usage"]["total_tokens"] == 15


def test_json_formatter_elk_shape() -> None:
    line = format_log_event(
        "http_request_end",
        request_id="r1",
        latency_ms=12.3,
        message="done",
    )
    payload = json.loads(line)
    assert payload["event"] == "http_request_end"
    assert "@timestamp" in payload
    assert payload["service"] == "enterprise-ai-agent"
    assert payload["latency_ms"] == 12.3


def test_log_query_by_request_and_user(tmp_path: Path) -> None:
    clear_log_store()
    clear_context()
    configure_structured_logging(log_file=tmp_path / "test.ndjson")

    set_request_id("req-q")
    set_user_id("alice")
    log_event("agent_execution", agent_id="chat", latency_ms=100.0)
    log_event("http_request_end", latency_ms=50.0)

    set_request_id("req-other")
    set_user_id("bob")
    log_event("http_request_end", latency_ms=5.0)

    engine = LogQueryEngine(get_log_store())
    hits = engine.query(LogQuery(request_id="req-q"))
    assert len(hits) == 2
    assert all(h.get("request_id") == "req-q" for h in hits)

    alice = engine.query(LogQuery(user_id="alice", event="agent_execution"))
    assert len(alice) == 1
    assert alice[0]["agent_id"] == "chat"


def test_query_engine_ndjson_file(tmp_path: Path) -> None:
    path = tmp_path / "lines.ndjson"
    rows = [
        {"event": "a", "request_id": "1", "latency_ms": 10},
        {"event": "b", "request_id": "2", "latency_ms": 200},
    ]
    path.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    engine = LogQueryEngine.from_ndjson_file(path)
    slow = engine.query(LogQuery(min_latency_ms=100.0))
    assert len(slow) == 1
    assert slow[0]["request_id"] == "2"

    assert engine.summarize_by_event() == {"a": 1, "b": 1}
