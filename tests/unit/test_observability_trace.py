"""Task 6.4 Agent Observability tests."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.observability.event import llm_performance_event
from app.observability.event import tool_invocation_event
from app.observability.metrics import EnterpriseMetricsAggregator
from app.observability.trace import default_trace_registry
from app.observability.trace import render_execution_timeline
from app.observability.types import AgentSpanEvent
from app.observability.types import TraceEventType
from app.scheduler.scheduler import AgentScheduler


class _EchoAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "echo"

    def get_capabilities(self) -> list[str]:
        return ["echo"]

    def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            success=True,
            model="mock",
            content=f"echo:{context.user_message}",
        )


def test_runtime_auto_records_trace_and_timeline() -> None:
    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)
    scheduler = AgentScheduler(worker_count=1, auto_start=True)
    runtime = AgentRuntime(registry=reg, default_agent="echo", scheduler=scheduler)
    scheduler.set_executor(runtime.execute_task)

    result = runtime.run(
        AgentTask(session_id="obs-s1", user_message="hello trace", agent_name="echo"),
    )

    assert result.success is True

    traces = default_trace_registry.list_session("obs-s1")
    assert len(traces) >= 1

    trace = traces[-1]
    assert trace.duration is not None

    agent_events = [
        event
        for event in trace.events
        if isinstance(event, AgentSpanEvent)
    ]
    assert any(event.phase == "start" for event in agent_events)
    assert any(event.phase == "end" for event in agent_events)

    timeline = render_execution_timeline(trace)
    assert "Agent Execution Timeline" not in timeline
    assert "AGENT START" in timeline
    assert "AGENT END" in timeline
    assert "METRICS" in timeline


def test_enterprise_metrics_from_events() -> None:
    aggregator = EnterpriseMetricsAggregator()
    aggregator.record(
        llm_performance_event(
            model="demo",
            latency_ms=200.0,
            prompt_tokens=10,
            completion_tokens=50,
            ttft_ms=40.0,
        )
    )
    aggregator.record(
        tool_invocation_event(
            tool_name="search",
            arguments={"q": "x"},
            duration_ms=12.0,
        )
    )

    summary = aggregator.summarize()
    assert summary["llm_call_count"] == 1
    assert summary["tool_call_count"] == 1
    assert aggregator.enterprise.ttft_ms == 40.0
    assert aggregator.enterprise.tokens_per_second is not None
