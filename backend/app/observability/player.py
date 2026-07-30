from app.core.logger import logger
from app.observability.types import LLMEvent
from app.observability.types import MemoryEvent
from app.observability.types import MultiAgentEvent
from app.observability.types import ObservationEvent
from app.observability.types import PlannerEvent
from app.observability.types import PromptEvent
from app.observability.types import RetrievalEvent
from app.observability.types import ToolEvent
from app.observability.types import Trace
from app.observability.types import TraceEvent
from app.observability.types import WorkflowEvent


class TracePlayer:
    """
    Trace 回放器。

    根据 Trace 重放执行过程，无需重新调用 LLM。
    用于调试 Prompt、Tool、RAG、Planner。
    """

    def __init__(
        self,
        trace: Trace,
    ):

        self._trace = trace

    @property
    def trace(self) -> Trace:
        return self._trace

    def play(
        self,
        verbose: bool = True,
    ) -> list[str]:

        lines: list[str] = []

        header = (
            f"Replay trace_id={self._trace.trace_id} "
            f"session_id={self._trace.session_id} "
            f"events={len(self._trace.events)} "
            f"duration={self._trace.duration or 0:.3f}s"
        )

        lines.append(header)

        if verbose:

            logger.info(header)

        for index, event in enumerate(self._trace.events):

            line = self._format_event(index, event)

            lines.append(line)

            if verbose:

                logger.info(line)

        return lines

    def _format_event(
        self,
        index: int,
        event: TraceEvent,
    ) -> str:

        if isinstance(event, PromptEvent):

            return (
                f"[{index}] PROMPT messages={event.message_count} "
                f"length={event.prompt_length} "
                f"tokens={event.token_count}"
            )

        if isinstance(event, LLMEvent):

            return (
                f"[{index}] LLM model={event.model} "
                f"duration={event.duration_ms:.1f}ms "
                f"tokens={event.prompt_tokens}+{event.completion_tokens} "
                f"tool_calls={event.tool_call_count} "
                f"preview={event.content_preview[:80]!r}"
            )

        if isinstance(event, ToolEvent):

            status = "ok" if event.success else "fail"

            return (
                f"[{index}] TOOL {event.tool_name} "
                f"status={status} duration={event.duration_ms:.1f}ms "
                f"output={event.output[:80]!r}"
            )

        if isinstance(event, ObservationEvent):

            return (
                f"[{index}] OBSERVATION tool={event.tool_name} "
                f"id={event.tool_call_id} "
                f"content={event.content[:80]!r}"
            )

        if isinstance(event, MemoryEvent):

            return (
                f"[{index}] MEMORY session={event.session_id} "
                f"records={event.record_count} "
                f"memory={event.memory_record_count}"
            )

        if isinstance(event, RetrievalEvent):

            return (
                f"[{index}] RETRIEVAL query={event.query[:60]!r} "
                f"hits={event.hit_count}/{event.top_k} "
                f"provider={event.embedding_provider}"
            )

        if isinstance(event, PlannerEvent):

            return (
                f"[{index}] PLANNER action={event.action} "
                f"goal={event.goal[:60]!r} "
                f"steps={event.step_count} "
                f"status={event.plan_status}"
            )

        if isinstance(event, WorkflowEvent):

            return (
                f"[{index}] WORKFLOW action={event.action} "
                f"mode={event.workflow_mode} "
                f"step={event.current_step_id} "
                f"success={event.success}"
            )

        if isinstance(event, MultiAgentEvent):

            return (
                f"[{index}] MULTI_AGENT action={event.action} "
                f"agent={event.agent_name} "
                f"selected={event.selected_agent} "
                f"task={event.task_id}"
            )

        return (
            f"[{index}] {event.event_type.value} "
            f"event_id={event.event_id}"
        )
