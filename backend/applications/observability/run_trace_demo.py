"""
Task 6.4 Observability Demo — Agent Execution Timeline。

运行:
    cd backend
    python -m applications.observability.run_trace_demo
"""

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
from app.observability.trace import default_trace_registry
from app.observability.trace import render_execution_timeline
from app.observability.types import TraceEventType
from app.scheduler.scheduler import AgentScheduler


class DemoAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "demo"

    def get_capabilities(self) -> list[str]:
        return ["demo"]

    def execute(self, context: AgentContext) -> AgentResult:
        from app.observability.trace import get_active_trace_collector

        collector = get_active_trace_collector()

        if collector is not None:
            collector.record(
                tool_invocation_event(
                    tool_name="echo",
                    arguments={"message": context.user_message},
                    output="ok",
                    duration_ms=5.0,
                )
            )
            collector.record(
                llm_performance_event(
                    model="demo-llm",
                    latency_ms=120.0,
                    prompt_tokens=20,
                    completion_tokens=40,
                    ttft_ms=35.0,
                    content_preview="generated",
                )
            )

        return AgentResult(
            success=True,
            model="demo-llm",
            content=f"answer:{context.user_message}",
        )


def main() -> None:
    print("Agent Observability Demo (Task 6.4)")

    reg = AgentRegistry()
    reg.register("demo", DemoAgent)
    scheduler = AgentScheduler(worker_count=1, auto_start=True)
    runtime = AgentRuntime(registry=reg, default_agent="demo", scheduler=scheduler)
    scheduler.set_executor(runtime.execute_task)

    session_id = "trace-demo-session"
    runtime.run(
        AgentTask(
            session_id=session_id,
            user_message="Explain observability",
            agent_name="demo",
        ),
    )

    traces = default_trace_registry.list_session(session_id)
    if not traces:
        print("No trace recorded.")
        return

    trace = traces[-1]
    timeline = render_execution_timeline(trace)
    print("\n--- Agent Execution Timeline ---")
    print(timeline)
    print("--------------------------------")


if __name__ == "__main__":
    main()
