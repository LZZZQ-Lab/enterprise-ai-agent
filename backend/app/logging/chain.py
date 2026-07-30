"""
Task 4.6：从 Trace 构建完整 Agent 执行链路文档。
"""

from __future__ import annotations

from typing import Any

from app.observability.serialization import trace_to_dict
from app.observability.types import LLMEvent
from app.observability.types import PlannerEvent
from app.observability.types import PromptEvent
from app.observability.types import ToolEvent
from app.observability.types import Trace
from app.observability.types import WorkflowEvent


def _step_from_event(
    index: int,
    event: Any,
) -> dict[str, Any]:

    base = {
        "index": index,
        "type": event.event_type.value,
        "event_id": event.event_id,
        "timestamp": event.timestamp,
    }

    if isinstance(event, PromptEvent):

        return {
            **base,
            "kind": "agent_step",
            "step": "prompt_build",
            "message_count": event.message_count,
            "prompt_tokens": event.token_count or 0,
        }

    if isinstance(event, LLMEvent):

        return {
            **base,
            "kind": "llm_call",
            "model": event.model,
            "duration_ms": event.duration_ms,
            "tool_call_count": event.tool_call_count,
            "prompt_tokens": event.prompt_tokens,
            "completion_tokens": event.completion_tokens,
            "error": event.error,
        }

    if isinstance(event, ToolEvent):

        return {
            **base,
            "kind": "tool_call",
            "tool_name": event.tool_name,
            "success": event.success,
            "duration_ms": event.duration_ms,
            "error": event.error,
        }

    if isinstance(event, PlannerEvent):

        return {
            **base,
            "kind": "agent_step",
            "step": event.action,
            "plan_status": event.plan_status,
            "step_id": event.step_id,
            "step_count": event.step_count,
        }

    if isinstance(event, WorkflowEvent):

        return {
            **base,
            "kind": "agent_step",
            "step": event.action,
            "success": event.success,
        }

    return base


def summarize_tokens(trace: Trace) -> dict[str, int]:

    prompt_tokens = 0
    completion_tokens = 0

    llm_events = [
        event
        for event in trace.events
        if isinstance(event, LLMEvent)
    ]

    if llm_events:

        for event in llm_events:

            prompt_tokens += event.prompt_tokens
            completion_tokens += event.completion_tokens

    else:

        for event in trace.events:

            if isinstance(event, PromptEvent) and event.token_count:

                prompt_tokens += event.token_count

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def build_agent_chain(
    trace: Trace,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    完整 Agent 链路（Request ID + 步骤 + Tool/LLM + Token 汇总）。
    """

    steps = [
        _step_from_event(index, event)
        for index, event in enumerate(trace.events)
    ]

    token_summary = summarize_tokens(trace)

    llm_calls = sum(
        1 for event in trace.events if isinstance(event, LLMEvent)
    )

    tool_calls = sum(
        1 for event in trace.events if isinstance(event, ToolEvent)
    )

    request_id = (
        request_id
        or trace.metadata.get("request_id")
        or ""
    )

    from observability.logging.context import get_log_context

    obs_ctx = get_log_context()

    return {
        "request_id": request_id,
        "trace_id": trace.trace_id,
        "session_id": trace.session_id,
        "user_id": obs_ctx.get("user_id") or trace.metadata.get("user_id"),
        "project_id": obs_ctx.get("project_id") or trace.metadata.get("project_id"),
        "agent_id": obs_ctx.get("agent_id") or trace.metadata.get("agent_name"),
        "workflow_id": obs_ctx.get("workflow_id") or trace.metadata.get("workflow_id"),
        "duration_sec": trace.duration,
        "latency_ms": round(trace.duration * 1000, 3) if trace.duration else None,
        "token_usage": obs_ctx.get("token_usage") or token_summary,
        "metadata": trace.metadata,
        "summary": {
            "step_count": len(steps),
            "llm_call_count": llm_calls,
            "tool_call_count": tool_calls,
            **token_summary,
        },
        "steps": steps,
        "trace": trace_to_dict(trace),
    }


def format_agent_chain_text(chain: dict[str, Any]) -> str:
    """人类可读的链路摘要（用于日志 / 调试）。"""

    summary = chain.get("summary") or {}

    lines = [
        "=== Agent Execution Chain ===",
        f"request_id={chain.get('request_id')}",
        f"trace_id={chain.get('trace_id')}",
        f"session_id={chain.get('session_id')}",
    ]

    duration = chain.get("duration_sec")

    if duration is not None:

        lines.append(f"duration={duration:.3f}s")

    else:

        lines.append("duration=N/A")

    lines.extend(
        [
            (
                f"tokens prompt={summary.get('prompt_tokens', 0)} "
                f"completion={summary.get('completion_tokens', 0)} "
                f"total={summary.get('total_tokens', 0)}"
            ),
            (
                f"llm_calls={summary.get('llm_call_count', 0)} "
                f"tool_calls={summary.get('tool_call_count', 0)}"
            ),
            "--- steps ---",
        ]
    )

    for step in chain.get("steps") or []:

        label = (
            step.get("step")
            or step.get("tool_name")
            or step.get("model")
            or ""
        )

        lines.append(
            f"[{step.get('index')}] "
            f"{step.get('kind')}/{step.get('type')} {label}"
        )

    return "\n".join(lines)
