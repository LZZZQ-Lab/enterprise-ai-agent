#!/usr/bin/env python3
"""Task 8.7 日志查询 Demo：写入 NDJSON 并按字段检索。"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from observability.logging.context import clear_context
from observability.logging.context import set_agent_id
from observability.logging.context import set_project_id
from observability.logging.context import set_request_id
from observability.logging.context import set_user_id
from observability.logging.context import set_workflow_id
from observability.logging.logger import clear_log_store
from observability.logging.logger import configure_structured_logging
from observability.logging.logger import get_log_store
from observability.logging.logger import log_agent_execution
from observability.logging.logger import log_event
from observability.logging.logger import log_http_request
from observability.logging.query import LogQuery
from observability.logging.query import LogQueryEngine


def _write_ndjson(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, ensure_ascii=False, default=str) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out_dir = BACKEND / "artifacts" / "logs"
    ndjson_path = out_dir / "structured.ndjson"
    clear_log_store()

    configure_structured_logging(log_file=ndjson_path)

    print("== 1. 写入结构化 JSON 日志 ==")

    set_request_id("req-demo-001")
    set_user_id("alice")
    set_project_id("proj-kb-01")
    set_agent_id("chat")
    set_workflow_id("wf-team-v1")

    log_http_request(
        phase="request_start",
        method="POST",
        path="/api/v1/chat",
    )
    time.sleep(0.01)
    log_http_request(
        phase="request_end",
        method="POST",
        path="/api/v1/chat",
        status_code=200,
        latency_ms=842.5,
    )
    log_agent_execution(
        agent_id="chat",
        workflow_id="wf-team-v1",
        project_id="proj-kb-01",
        token_usage={
            "prompt_tokens": 128,
            "completion_tokens": 64,
            "total_tokens": 192,
        },
        latency_ms=820.0,
        model="Qwen2.5",
        success=True,
    )
    log_event("agent_chain_complete", trace_id="trace-abc", summary={"total_tokens": 192})

    set_request_id("req-demo-002")
    set_user_id("bob")
    log_http_request(
        phase="request_end",
        method="GET",
        path="/health",
        status_code=200,
        latency_ms=3.2,
    )

    clear_context()
    records = get_log_store()
    print(f"内存记录数: {len(records)}")
    print(f"NDJSON 文件: {ndjson_path}")

    print("\n== 2. 按 Request ID 查询 ==")
    engine = LogQueryEngine.from_ndjson_file(ndjson_path)
    by_req = engine.query(LogQuery(request_id="req-demo-001"))
    for row in by_req:
        print(f"  [{row.get('event')}] latency={row.get('latency_ms')} user={row.get('user_id')}")

    print("\n== 3. 按 User ID 查询 ==")
    by_user = engine.query(LogQuery(user_id="alice"))
    print(f"  alice 相关日志: {len(by_user)} 条")

    print("\n== 4. 按 Agent + Workflow 查询 ==")
    by_agent = engine.query(
        LogQuery(agent_id="chat", workflow_id="wf-team-v1", event="agent_execution")
    )
    if by_agent:
        usage = by_agent[0].get("token_usage", {})
        print(f"  token_usage={usage}")

    print("\n== 5. 聚合统计 ==")
    print(f"  事件分布: {engine.summarize_by_event()}")
    print(f"  Token 合计: {engine.total_token_usage()}")

    print("\n== ELK / Loki 接入提示 ==")
    print("  - Filebeat / Promtail 采集 artifacts/logs/structured.ndjson")
    print("  - Loki label 建议: service, event, level")
    print("  - Elasticsearch index: enterprise-ai-agent-*")

    print("\nDemo 完成.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
