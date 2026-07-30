"""
企业可观测性事件工厂（Task 6.4）。

与 ``app.observability.types`` 中的 TraceEvent 子类配合使用。
"""

from __future__ import annotations

import time
from typing import Any

from app.monitoring.collector import GpuSnapshot
from app.monitoring.collector import collect_gpu_snapshot
from app.monitoring.tokens import estimate_token_count
from app.observability.types import AgentSpanEvent
from app.observability.types import GPUMetricsEvent
from app.observability.types import LLMEvent
from app.observability.types import ToolEvent
from app.observability.types import TraceEventType


def agent_start_event(
    *,
    agent_name: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> AgentSpanEvent:
    prompt_tokens = estimate_token_count(prompt)

    return AgentSpanEvent(
        event_type=TraceEventType.AGENT,
        timestamp=time.time(),
        agent_name=agent_name,
        phase="start",
        prompt=prompt,
        prompt_tokens=prompt_tokens,
        total_tokens=prompt_tokens,
    )


def agent_end_event(
    *,
    agent_name: str,
    prompt: str,
    response: str,
    started_at: float,
    success: bool,
    tool_call_count: int = 0,
) -> AgentSpanEvent:
    ended = time.time()
    duration_ms = max(0.0, (ended - started_at) * 1000.0)
    prompt_tokens = estimate_token_count(prompt)
    completion_tokens = estimate_token_count(response)

    return AgentSpanEvent(
        event_type=TraceEventType.AGENT,
        timestamp=ended,
        agent_name=agent_name,
        phase="end",
        prompt=prompt,
        response=response,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        duration_ms=duration_ms,
        success=success,
        tool_call_count=tool_call_count,
    )


def gpu_snapshot_event(
    snapshot: GpuSnapshot,
    *,
    phase: str,
) -> GPUMetricsEvent:
    return GPUMetricsEvent(
        event_type=TraceEventType.GPU,
        timestamp=time.time(),
        memory_used_mib=snapshot.memory_used_mib,
        memory_total_mib=snapshot.memory_total_mib,
        utilization_percent=snapshot.utilization_percent,
        gpu_index=snapshot.gpu_index,
        phase=phase,
    )


def gpu_event_from_collector(
    *,
    phase: str,
    gpu_index: int = 0,
) -> GPUMetricsEvent:
    return gpu_snapshot_event(
        collect_gpu_snapshot(gpu_index),
        phase=phase,
    )


def llm_performance_event(
    *,
    model: str,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    ttft_ms: float | None = None,
    content_preview: str = "",
    error: str | None = None,
) -> LLMEvent:
    tps: float | None = None

    if completion_tokens > 0 and latency_ms > 0:
        tps = completion_tokens / (latency_ms / 1000.0)

    if ttft_ms is None and latency_ms > 0:
        ttft_ms = latency_ms * 0.2

    return LLMEvent(
        event_type=TraceEventType.LLM,
        timestamp=time.time(),
        model=model,
        content_preview=content_preview,
        duration_ms=latency_ms,
        ttft_ms=ttft_ms,
        tokens_per_second=tps,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        error=error,
    )


def tool_invocation_event(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    output: str = "",
    success: bool = True,
    duration_ms: float = 0.0,
    error: str | None = None,
) -> ToolEvent:
    return ToolEvent(
        event_type=TraceEventType.TOOL,
        timestamp=time.time(),
        tool_name=tool_name,
        arguments=arguments,
        output=output,
        success=success,
        duration_ms=duration_ms,
        error=error,
    )
