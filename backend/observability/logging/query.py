"""Task 8.7: query structured JSON logs (ELK / Loki style filters)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterator


@dataclass
class LogQuery:
    request_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
    workflow_id: str | None = None
    event: str | None = None
    min_latency_ms: float | None = None
    limit: int = 100


class LogQueryEngine:
    """对 NDJSON 日志文件或内存记录执行过滤查询。"""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self._records = records or []

    @classmethod
    def from_ndjson_file(cls, path: Path | str) -> LogQueryEngine:
        records: list[dict[str, Any]] = []
        text = Path(path).read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return cls(records)

    def add_records(self, records: list[dict[str, Any]]) -> None:
        self._records.extend(records)

    def query(self, q: LogQuery | None = None) -> list[dict[str, Any]]:
        q = q or LogQuery()
        results: list[dict[str, Any]] = []

        for record in self._records:
            if q.request_id and record.get("request_id") != q.request_id:
                continue
            if q.user_id and record.get("user_id") != q.user_id:
                continue
            if q.project_id and record.get("project_id") != q.project_id:
                continue
            if q.agent_id and record.get("agent_id") != q.agent_id:
                continue
            if q.workflow_id and record.get("workflow_id") != q.workflow_id:
                continue
            if q.event and record.get("event") != q.event:
                continue
            latency = record.get("latency_ms")
            if q.min_latency_ms is not None:
                if latency is None or float(latency) < q.min_latency_ms:
                    continue
            results.append(record)
            if len(results) >= q.limit:
                break

        return results

    def summarize_by_event(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self._records:
            event = str(record.get("event", "unknown"))
            counts[event] = counts.get(event, 0) + 1
        return counts

    def total_token_usage(self) -> dict[str, int]:
        prompt = completion = total = 0
        for record in self._records:
            usage = record.get("token_usage") or {}
            prompt += int(usage.get("prompt_tokens") or 0)
            completion += int(usage.get("completion_tokens") or 0)
            total += int(usage.get("total_tokens") or 0)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total or prompt + completion,
        }

    def iter_records(self) -> Iterator[dict[str, Any]]:
        yield from self._records
