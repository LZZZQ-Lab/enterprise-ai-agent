from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.observability.types import LLMEvent
from app.observability.types import PlannerEvent
from app.observability.types import PromptEvent
from app.observability.types import RetrievalEvent
from app.observability.types import ToolEvent
from app.observability.types import Trace
from app.observability.types import TraceEvent
from app.observability.types import TraceEventType
from app.observability.types import AgentSpanEvent
from app.observability.types import GPUMetricsEvent


@dataclass
class TraceMetrics:
    """
    一次 Agent 执行的统计指标。
    """

    llm_call_count: int = 0

    tool_call_count: int = 0

    tool_success_count: int = 0

    tool_failure_count: int = 0

    total_duration_ms: float = 0.0

    llm_duration_ms: float = 0.0

    tool_duration_ms: float = 0.0

    plan_step_count: int = 0

    prompt_length: int = 0

    rag_hit_count: int = 0

    @property
    def tool_success_rate(self) -> float:

        if self.tool_call_count == 0:

            return 1.0

        return (
            self.tool_success_count
            / self.tool_call_count
        )

    @property
    def average_llm_duration_ms(self) -> float:

        if self.llm_call_count == 0:

            return 0.0

        return self.llm_duration_ms / self.llm_call_count

    @property
    def average_tool_duration_ms(self) -> float:

        if self.tool_call_count == 0:

            return 0.0

        return self.tool_duration_ms / self.tool_call_count


class MetricsCollector:
    """
    从 TraceEvent 聚合 Metrics。
    """

    def __init__(self):

        self._metrics = TraceMetrics()

    @property
    def metrics(self) -> TraceMetrics:
        return self._metrics

    def reset(self) -> None:

        self._metrics = TraceMetrics()

    def record(self, event: TraceEvent) -> None:

        if isinstance(event, LLMEvent):

            self._metrics.llm_call_count += 1
            self._metrics.llm_duration_ms += event.duration_ms

        elif isinstance(event, ToolEvent):

            self._metrics.tool_call_count += 1
            self._metrics.tool_duration_ms += event.duration_ms

            if event.success:

                self._metrics.tool_success_count += 1

            else:

                self._metrics.tool_failure_count += 1

        elif isinstance(event, PromptEvent):

            self._metrics.prompt_length = max(
                self._metrics.prompt_length,
                event.prompt_length,
            )

        elif isinstance(event, RetrievalEvent):

            self._metrics.rag_hit_count += event.hit_count

        elif isinstance(event, PlannerEvent):

            if event.action in ("plan_created", "plan_complete"):

                self._metrics.plan_step_count = max(
                    self._metrics.plan_step_count,
                    event.step_count,
                )

    def summarize(self) -> dict:

        metrics = self._metrics

        return {
            "llm_call_count": metrics.llm_call_count,
            "tool_call_count": metrics.tool_call_count,
            "tool_success_rate": metrics.tool_success_rate,
            "average_llm_duration_ms": (
                metrics.average_llm_duration_ms
            ),
            "average_tool_duration_ms": (
                metrics.average_tool_duration_ms
            ),
            "plan_step_count": metrics.plan_step_count,
            "prompt_length": metrics.prompt_length,
            "rag_hit_count": metrics.rag_hit_count,
        }


@dataclass
class EnterpriseTraceMetrics:
    """
    企业级 Trace 指标（Task 6.4）。
    """

    agent_duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_call_count: int = 0
    llm_call_count: int = 0
    llm_latency_ms: float = 0.0
    ttft_ms: float = 0.0
    tokens_per_second: float = 0.0
    gpu_memory_used_mib: float | None = None
    gpu_utilization_percent: float | None = None


class EnterpriseMetricsAggregator(MetricsCollector):
    """
    扩展 MetricsCollector，聚合 LLM / GPU / Agent 跨度指标。
    """

    def __init__(self) -> None:
        super().__init__()
        self.enterprise = EnterpriseTraceMetrics()

    def record(self, event: TraceEvent) -> None:
        super().record(event)

        if isinstance(event, AgentSpanEvent) and event.phase == "end":
            self.enterprise.agent_duration_ms = max(
                self.enterprise.agent_duration_ms,
                event.duration_ms,
            )
            self.enterprise.prompt_tokens = event.prompt_tokens
            self.enterprise.completion_tokens = event.completion_tokens
            self.enterprise.total_tokens = event.total_tokens
            self.enterprise.tool_call_count = max(
                self.enterprise.tool_call_count,
                event.tool_call_count,
            )

        elif isinstance(event, LLMEvent):
            self.enterprise.llm_call_count += 1
            self.enterprise.llm_latency_ms += event.duration_ms

            if event.ttft_ms is not None:
                self.enterprise.ttft_ms = max(
                    self.enterprise.ttft_ms,
                    event.ttft_ms,
                )

            if event.tokens_per_second is not None:
                self.enterprise.tokens_per_second = max(
                    self.enterprise.tokens_per_second,
                    event.tokens_per_second,
                )

            self.enterprise.prompt_tokens += event.prompt_tokens
            self.enterprise.completion_tokens += event.completion_tokens
            self.enterprise.total_tokens = (
                self.enterprise.prompt_tokens
                + self.enterprise.completion_tokens
            )

        elif isinstance(event, ToolEvent):
            self.enterprise.tool_call_count = self.metrics.tool_call_count

        elif isinstance(event, GPUMetricsEvent):
            if event.phase == "agent_end":
                self.enterprise.gpu_memory_used_mib = event.memory_used_mib
                self.enterprise.gpu_utilization_percent = (
                    event.utilization_percent
                )

    @staticmethod
    def summarize_trace(trace: Trace) -> dict[str, Any]:
        aggregator = EnterpriseMetricsAggregator()

        for event in trace.events:
            aggregator.record(event)

        ent = aggregator.enterprise
        base = aggregator.summarize()

        return {
            **base,
            "agent_duration_ms": ent.agent_duration_ms,
            "total_tokens": ent.total_tokens,
            "prompt_tokens": ent.prompt_tokens,
            "completion_tokens": ent.completion_tokens,
            "llm_latency_ms": ent.llm_latency_ms,
            "ttft_ms": ent.ttft_ms,
            "tokens_per_second": ent.tokens_per_second,
            "gpu_memory_used_mib": ent.gpu_memory_used_mib,
            "gpu_utilization_percent": ent.gpu_utilization_percent,
        }
