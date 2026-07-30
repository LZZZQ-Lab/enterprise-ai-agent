import time
from typing import TYPE_CHECKING

from app.core.logger import logger
from app.llm.types import Message
from app.llm.types import ToolCall
from app.observability.types import LLMEvent
from app.observability.types import MemoryEvent
from app.observability.types import MultiAgentEvent
from app.observability.types import ObservationEvent
from app.observability.types import PlannerEvent
from app.observability.types import PlannerStepSnapshot
from app.observability.types import PromptEvent
from app.observability.types import RetrievalDocument
from app.observability.types import RetrievalEvent
from app.observability.types import ToolEvent
from app.observability.types import TraceEventType
from app.observability.types import WorkflowEvent

from app.observability.trace import get_active_trace_collector

if TYPE_CHECKING:
    from app.agents.types import AgentResult
    from app.observability.collector import TraceCollector


class AgentTracer:
    """
    Agent 执行追踪，便于 Debug。

    可选接入 TraceCollector，统一收集 TraceEvent。
    enable_trace=False 时行为与 Task10 一致。
    """

    def __init__(
        self,
        trace_collector: "TraceCollector | None" = None,
    ):

        self._collector = trace_collector

    def _record(self, event) -> None:

        if self._collector is not None:

            self._collector.record(event)

        active = get_active_trace_collector()

        if active is not None and active is not self._collector:

            active.record(event)

    @staticmethod
    def _serialize_messages(
        messages: list[Message],
    ) -> list[dict]:

        return [
            {
                "role": message.role,
                "content": message.content or "",
                "tool_call_id": message.tool_call_id,
                "name": message.name,
            }
            for message in messages
        ]

    @staticmethod
    def _prompt_length(
        messages: list[Message],
    ) -> int:

        return sum(
            len(message.content or "")
            for message in messages
        )

    def on_prompt(
        self,
        messages: list[Message],
    ) -> None:

        from app.monitoring.tokens import estimate_token_count

        prompt_text = "".join(
            message.content or ""
            for message in messages
        )

        token_count = estimate_token_count(prompt_text)

        logger.info(
            "Agent prompt built: %d message(s) ~%d tokens",
            len(messages),
            token_count,
        )

        for index, message in enumerate(messages):

            preview = (message.content or "")[:120]

            logger.debug(
                "  [%d] role=%s content=%s",
                index,
                message.role,
                preview,
            )

        self._record(
            PromptEvent(
                event_type=TraceEventType.PROMPT,
                timestamp=time.time(),
                messages=self._serialize_messages(messages),
                message_count=len(messages),
                prompt_length=self._prompt_length(messages),
                token_count=token_count,
            )
        )

    def on_llm_call(
        self,
        *,
        model: str,
        input_message_count: int,
        content_preview: str = "",
        has_tool_calls: bool = False,
        tool_call_count: int = 0,
        duration_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        ttft_ms: float | None = None,
        tokens_per_second: float | None = None,
        error: str | None = None,
    ) -> None:

        if tokens_per_second is None and completion_tokens > 0 and duration_ms > 0:
            tokens_per_second = completion_tokens / (duration_ms / 1000.0)

        if ttft_ms is None and duration_ms > 0:
            ttft_ms = duration_ms * 0.2

        logger.info(
            "Agent LLM call: model=%s duration=%.1fms ttft=%.1fms tps=%.1f "
            "tool_calls=%d tokens=%d+%d",
            model,
            duration_ms,
            ttft_ms or 0.0,
            tokens_per_second or 0.0,
            tool_call_count,
            prompt_tokens,
            completion_tokens,
        )

        self._record(
            LLMEvent(
                event_type=TraceEventType.LLM,
                timestamp=time.time(),
                model=model,
                input_message_count=input_message_count,
                content_preview=content_preview,
                has_tool_calls=has_tool_calls,
                tool_call_count=tool_call_count,
                duration_ms=duration_ms,
                ttft_ms=ttft_ms,
                tokens_per_second=tokens_per_second,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error,
            )
        )

    @staticmethod
    def _safe_log_value(value, limit: int = 300) -> str:

        text = str(value)

        if len(text) > limit:

            text = f"{text[:limit]}...(truncated)"

        return text.encode("utf-8", errors="replace").decode("utf-8")

    def on_tool_call(
        self,
        tool_call: ToolCall,
        *,
        output: str = "",
        success: bool = True,
        duration_ms: float = 0.0,
        error: str | None = None,
    ) -> None:

        logger.info(
            "Agent tool call: %s args=%s",
            tool_call.name,
            self._safe_log_value(tool_call.arguments),
        )

        self._record(
            ToolEvent(
                event_type=TraceEventType.TOOL,
                timestamp=time.time(),
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                output=output,
                success=success,
                duration_ms=duration_ms,
                error=error,
            )
        )

    def on_observation(
        self,
        message: Message,
    ) -> None:

        preview = (message.content or "")[:120]

        logger.info(
            "Agent observation: tool_call_id=%s content=%s",
            message.tool_call_id,
            preview,
        )

        self._record(
            ObservationEvent(
                event_type=TraceEventType.OBSERVATION,
                timestamp=time.time(),
                tool_call_id=message.tool_call_id or "",
                tool_name=message.name or "",
                content=message.content or "",
            )
        )

    def on_embodied_observation(
        self,
        observation,
        *,
        iteration: int = 0,
    ) -> None:
        """
        记录具身智能 Observation。

        在 Action -> Environment -> Observation 阶段触发。
        """

        logger.info(
            "Embodied observation: iteration=%d type=%s content=%s",
            iteration,
            observation.type,
            (observation.content or "")[:120],
        )

        self._record(
            ObservationEvent(
                event_type=TraceEventType.OBSERVATION,
                timestamp=time.time(),
                tool_call_id="",
                tool_name=observation.source or observation.type,
                content=observation.to_prompt_text(),
            )
        )

    def on_memory_load(
        self,
        session_id: str,
        record_count: int,
        memory_record_count: int,
    ) -> None:

        logger.info(
            "Memory loaded session=%s records=%d memory=%d",
            session_id,
            record_count,
            memory_record_count,
        )

        self._record(
            MemoryEvent(
                event_type=TraceEventType.MEMORY,
                timestamp=time.time(),
                session_id=session_id,
                record_count=record_count,
                memory_record_count=memory_record_count,
            )
        )

    def on_final_answer(
        self,
        result: "AgentResult",
    ) -> None:

        preview = (result.content or "")[:120]

        logger.info(
            "Agent final answer: success=%s model=%s content=%s",
            result.success,
            result.model,
            preview,
        )

        self._record(
            WorkflowEvent(
                event_type=TraceEventType.WORKFLOW,
                timestamp=time.time(),
                action="final_answer",
                success=result.success,
                content_preview=result.content or "",
            )
        )

    def on_rag_retrieval(
        self,
        query: str,
        results,
        *,
        embedding_provider: str = "",
        top_k: int = 0,
        injected_content: str = "",
    ) -> None:

        logger.info(
            "RAG retrieval query=%s hits=%d",
            query[:120],
            len(results),
        )

        documents: list[RetrievalDocument] = []

        for index, scored in enumerate(results):

            preview = scored.document.content[:120]

            logger.info(
                "  RAG [%d] id=%s score=%.4f content=%s",
                index,
                scored.document.id,
                scored.score,
                preview,
            )

            documents.append(
                RetrievalDocument(
                    document_id=scored.document.id,
                    score=scored.score,
                    content_preview=preview,
                    source=scored.document.metadata.get(
                        "source",
                        "",
                    ),
                )
            )

        self._record(
            RetrievalEvent(
                event_type=TraceEventType.RETRIEVAL,
                timestamp=time.time(),
                query=query,
                embedding_provider=embedding_provider,
                top_k=top_k,
                hit_count=len(results),
                documents=documents,
                injected_content=injected_content,
            )
        )

    def on_mcp_server(
        self,
        server_name: str,
        action: str,
    ) -> None:

        logger.info(
            "MCP server %s: %s",
            server_name,
            action,
        )

    def on_mcp_tool_call(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ) -> None:

        logger.info(
            "MCP tool call server=%s tool=%s args=%s",
            server_name,
            tool_name,
            arguments,
        )

    def on_mcp_resource(
        self,
        server_name: str,
        resource_id: str,
        content_preview: str = "",
    ) -> None:

        logger.info(
            "MCP resource server=%s id=%s preview=%s",
            server_name,
            resource_id,
            content_preview[:120],
        )

    def on_mcp_prompt(
        self,
        server_name: str,
        prompt_name: str,
    ) -> None:

        logger.info(
            "MCP prompt server=%s name=%s",
            server_name,
            prompt_name,
        )

    @staticmethod
    def _plan_step_snapshots(plan) -> list[PlannerStepSnapshot]:

        return [
            PlannerStepSnapshot(
                step_id=step.id,
                description=step.description,
                tool=step.tool,
                status=step.status.value,
                result=step.result,
            )
            for step in plan.steps
        ]

    def on_plan_created(
        self,
        plan,
    ) -> None:

        logger.info(
            "Plan created goal=%s steps=%d status=%s",
            plan.goal[:120],
            len(plan.steps),
            plan.status.value,
        )

        for step in plan.steps:

            logger.info(
                "  Plan step [%s] tool=%s desc=%s",
                step.id,
                step.tool,
                step.description[:120],
            )

        self._record(
            PlannerEvent(
                event_type=TraceEventType.PLANNER,
                timestamp=time.time(),
                action="plan_created",
                goal=plan.goal,
                plan_status=plan.status.value,
                step_count=len(plan.steps),
                steps=self._plan_step_snapshots(plan),
            )
        )

    def on_plan_step_start(
        self,
        plan,
        step,
    ) -> None:

        logger.info(
            "Plan step started plan=%s step=%s status=%s",
            plan.goal[:60],
            step.id,
            step.status.value,
        )

        self._record(
            PlannerEvent(
                event_type=TraceEventType.PLANNER,
                timestamp=time.time(),
                action="step_start",
                goal=plan.goal,
                plan_status=plan.status.value,
                step_count=len(plan.steps),
                step_id=step.id,
            )
        )

        self._record(
            WorkflowEvent(
                event_type=TraceEventType.WORKFLOW,
                timestamp=time.time(),
                action="step_start",
                plan_status=plan.status.value,
                current_step_id=step.id,
            )
        )

    def on_plan_step_result(
        self,
        plan,
        step,
    ) -> None:

        preview = (step.result or "")[:120]

        logger.info(
            "Plan step result step=%s status=%s result=%s",
            step.id,
            step.status.value,
            preview,
        )

        self._record(
            PlannerEvent(
                event_type=TraceEventType.PLANNER,
                timestamp=time.time(),
                action="step_result",
                goal=plan.goal,
                plan_status=plan.status.value,
                step_count=len(plan.steps),
                step_id=step.id,
                step_result=step.result,
                steps=self._plan_step_snapshots(plan),
            )
        )

    def on_plan_complete(
        self,
        plan,
    ) -> None:

        logger.info(
            "Plan complete goal=%s status=%s",
            plan.goal[:120],
            plan.status.value,
        )

        self._record(
            PlannerEvent(
                event_type=TraceEventType.PLANNER,
                timestamp=time.time(),
                action="plan_complete",
                goal=plan.goal,
                plan_status=plan.status.value,
                step_count=len(plan.steps),
                steps=self._plan_step_snapshots(plan),
            )
        )

        self._record(
            WorkflowEvent(
                event_type=TraceEventType.WORKFLOW,
                timestamp=time.time(),
                action="plan_complete",
                plan_status=plan.status.value,
                success=plan.status.value == "completed",
            )
        )

    def on_workflow_start(
        self,
        workflow_mode: str,
    ) -> None:

        self._record(
            WorkflowEvent(
                event_type=TraceEventType.WORKFLOW,
                timestamp=time.time(),
                action="workflow_start",
                workflow_mode=workflow_mode,
            )
        )

    def on_agent_routing(
        self,
        *,
        task_input: str,
        selected_agent: str,
        goal: str = "",
    ) -> None:

        logger.info(
            "Agent routing input=%s selected=%s",
            task_input[:120],
            selected_agent,
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="agent_routing",
                task_input=task_input,
                selected_agent=selected_agent,
                content_preview=goal[:120],
            )
        )

    def on_coordinator_start(
        self,
        user_input: str,
        agent_count: int,
    ) -> None:

        logger.info(
            "Coordinator start input=%s agents=%d",
            user_input[:120],
            agent_count,
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="coordinator_start",
                task_input=user_input,
                content_preview=f"agents={agent_count}",
            )
        )

    def on_coordinator_dispatch(
        self,
        *,
        agent_name: str,
        task_id: str,
        success: bool,
    ) -> None:

        logger.info(
            "Coordinator dispatch agent=%s task=%s success=%s",
            agent_name,
            task_id,
            success,
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="coordinator_dispatch",
                agent_name=agent_name,
                task_id=task_id,
                success=success,
            )
        )

    def on_coordinator_complete(
        self,
        user_input: str,
        success: bool,
    ) -> None:

        logger.info(
            "Coordinator complete input=%s success=%s",
            user_input[:120],
            success,
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="coordinator_complete",
                task_input=user_input,
                success=success,
            )
        )

    def on_message_bus(
        self,
        *,
        sender: str,
        receiver: str,
        message_type: str,
        payload_preview: str = "",
    ) -> None:

        logger.info(
            "MessageBus %s -> %s type=%s",
            sender,
            receiver,
            message_type,
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="message_bus",
                agent_name=sender,
                selected_agent=receiver,
                message_type=message_type,
                content_preview=payload_preview[:120],
            )
        )

    def on_agent_execution(
        self,
        agent_name: str,
        task_flow: str = "",
    ) -> None:

        logger.info(
            "Agent execution name=%s flow=%s",
            agent_name,
            task_flow[:120],
        )

        self._record(
            MultiAgentEvent(
                event_type=TraceEventType.MULTI_AGENT,
                timestamp=time.time(),
                action="agent_execution",
                agent_name=agent_name,
                content_preview=task_flow[:120],
            )
        )

