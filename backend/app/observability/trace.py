"""
Agent Trace 会话、注册表与 Execution Timeline（Task 6.4）。
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from typing import Iterator

from app.observability.collector import TraceCollector
from app.observability.event import agent_end_event
from app.observability.event import agent_start_event
from app.observability.event import gpu_event_from_collector
from app.observability.logger import default_observability_logger
from app.observability.metrics import EnterpriseMetricsAggregator
from app.observability.types import AgentSpanEvent
from app.observability.types import LLMEvent
from app.observability.types import ToolEvent
from app.observability.types import Trace
from app.observability.types import TraceEvent
from app.observability.types import TraceEventType

_active_collector: ContextVar[TraceCollector | None] = ContextVar(
    "obs_active_trace_collector",
    default=None,
)


def get_active_trace_collector() -> TraceCollector | None:
    return _active_collector.get()


class TraceRegistry:
    """内存 Trace 索引（按 trace_id / session_id 查询）。"""

    def __init__(self) -> None:
        self._by_id: dict[str, Trace] = {}
        self._by_session: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def put(self, trace: Trace) -> None:
        with self._lock:
            self._by_id[trace.trace_id] = trace
            self._by_session.setdefault(trace.session_id, []).append(
                trace.trace_id,
            )

    def get(self, trace_id: str) -> Trace | None:
        with self._lock:
            return self._by_id.get(trace_id)

    def list_session(self, session_id: str) -> list[Trace]:
        with self._lock:
            ids = self._by_session.get(session_id, [])
            return [self._by_id[tid] for tid in ids if tid in self._by_id]


default_trace_registry = TraceRegistry()


@dataclass
class AgentExecutionTraceSession:
    """
    单次 Agent 执行的 Trace 会话。
    """

    session_id: str
    agent_name: str
    prompt: str
    metadata: dict[str, Any]
    collector: TraceCollector
    started_at: float
    _token: Any = None

    def record(self, event: TraceEvent) -> None:
        self.collector.record(event)

    def finish(
        self,
        *,
        response: str,
        success: bool,
    ) -> Trace | None:
        tool_count = 0
        current = self.collector.current_trace

        if current is not None:
            tool_count = sum(
                1 for event in current.events if isinstance(event, ToolEvent)
            )

        self.record(
            agent_end_event(
                agent_name=self.agent_name,
                prompt=self.prompt,
                response=response,
                started_at=self.started_at,
                success=success,
                tool_call_count=tool_count,
            )
        )
        self.record(gpu_event_from_collector(phase="agent_end"))

        trace = self.collector.finish_trace()

        if trace is not None:
            default_trace_registry.put(trace)
            timeline = render_execution_timeline(trace)
            default_observability_logger.trace_finished(
                trace,
                timeline=timeline,
            )

        if self._token is not None:
            _active_collector.reset(self._token)

        return trace


@contextmanager
def agent_execution_trace(
    *,
    session_id: str,
    agent_name: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
    registry: TraceRegistry | None = None,
) -> Iterator[AgentExecutionTraceSession]:
    """
    在 AgentRuntime 中自动包裹每次 Agent 执行。
    """

    del registry

    metrics = EnterpriseMetricsAggregator()
    collector = TraceCollector(metrics_collector=metrics)
    started_at = time.time()

    meta = dict(metadata or {})
    meta.setdefault("agent_name", agent_name)

    collector.start_trace(session_id=session_id, metadata=meta)
    collector.record(gpu_event_from_collector(phase="agent_start"))
    collector.record(
        agent_start_event(
            agent_name=agent_name,
            prompt=prompt,
        )
    )

    token = _active_collector.set(collector)
    session = AgentExecutionTraceSession(
        session_id=session_id,
        agent_name=agent_name,
        prompt=prompt,
        metadata=meta,
        collector=collector,
        started_at=started_at,
        _token=token,
    )

    try:
        yield session
    finally:
        if _active_collector.get() is collector:
            _active_collector.reset(token)


def render_execution_timeline(trace: Trace) -> str:
    """
    输出 Agent Execution Timeline（ASCII）。
    """

    if not trace.events:
        return f"[trace {trace.trace_id}] (no events)"

    origin = trace.start_time
    lines: list[str] = []
    header = (
        f"Trace {trace.trace_id} | session={trace.session_id} | "
        f"agent={trace.metadata.get('agent_name', '')}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    sorted_events = sorted(trace.events, key=lambda item: item.timestamp)

    for event in sorted_events:
        offset_ms = (event.timestamp - origin) * 1000.0
        label = _format_event_label(event)
        lines.append(f"+{offset_ms:8.1f}ms  {label}")

    if trace.duration is not None:
        lines.append(f"TOTAL {trace.duration * 1000.0:.1f}ms")

    summary = EnterpriseMetricsAggregator.summarize_trace(trace)
    lines.append(
        "METRICS "
        f"tokens={summary.get('total_tokens', 0)} "
        f"llm_latency_ms={summary.get('llm_latency_ms', 0):.1f} "
        f"ttft_ms={summary.get('ttft_ms', 0):.1f} "
        f"tps={summary.get('tokens_per_second', 0):.1f} "
        f"tools={summary.get('tool_call_count', 0)} "
        f"gpu_util={summary.get('gpu_utilization_percent')}"
    )

    return "\n".join(lines)


def _format_event_label(event: TraceEvent) -> str:
    kind = event.event_type.value

    if isinstance(event, AgentSpanEvent):
        if event.phase == "start":
            preview = event.prompt[:60].replace("\n", " ")
            return (
                f"[AGENT START] {event.agent_name} "
                f"prompt_tokens={event.prompt_tokens} "
                f"prompt={preview!r}"
            )
        preview = event.response[:60].replace("\n", " ")
        return (
            f"[AGENT END]   {event.agent_name} "
            f"ok={event.success} duration={event.duration_ms:.1f}ms "
            f"tokens={event.total_tokens} tools={event.tool_call_count} "
            f"response={preview!r}"
        )

    if isinstance(event, LLMEvent):
        return (
            f"[LLM] model={event.model} latency={event.duration_ms:.1f}ms "
            f"ttft={event.ttft_ms or 0:.1f}ms "
            f"tps={event.tokens_per_second or 0:.1f} "
            f"tokens={event.prompt_tokens}+{event.completion_tokens}"
        )

    if isinstance(event, ToolEvent):
        return (
            f"[TOOL] {event.tool_name} ok={event.success} "
            f"duration={event.duration_ms:.1f}ms"
        )

    if event.event_type == TraceEventType.GPU:
        from app.observability.types import GPUMetricsEvent

        if isinstance(event, GPUMetricsEvent):
            return (
                f"[GPU] phase={event.phase} "
                f"mem={event.memory_used_mib}/{event.memory_total_mib} MiB "
                f"util={event.utilization_percent}%"
            )

    return f"[{kind.upper()}] id={event.event_id[:8]}"
