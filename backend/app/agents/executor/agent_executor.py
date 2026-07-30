from typing import TYPE_CHECKING

import time

from app.core.logger import logger
from app.config import AgentConfig
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.tools.manager import ToolManager
from app.tools.types import ToolContext
from app.tools.types import ToolResult

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult
    from app.embodied.types import Observation
    from app.llm.client import LLMClient
    from app.llm.types import Message


class AgentExecutor:
    """
    Agent Loop 执行器。

    单一职责：驱动 LLM ↔ Tool 循环。
    Plan-and-Execute 由 WorkflowExecutor 编排，本类保持不变。
    """

    def __init__(
        self,
        client: "LLMClient",
        config: AgentConfig,
        tool_message_builder: ToolMessageBuilder,
        tool_manager: ToolManager,
        error_handler: AgentErrorHandler,
        tracer: AgentTracer,
    ):

        self._client = client
        self._config = config
        self._tool_message_builder = tool_message_builder
        self._tool_manager = tool_manager
        self._error_handler = error_handler
        self._tracer = tracer
        self._embodied_loop_helper = None

        if self._config.enable_embodied:

            from app.embodied.agent_loop import EmbodiedAgentLoopHelper
            from app.embodied.embodied_observation_builder import (
                EmbodiedObservationBuilder,
            )

            embodied_builder = EmbodiedObservationBuilder()

            if isinstance(
                tool_message_builder._observation_builder,
                EmbodiedObservationBuilder,
            ):

                embodied_builder = (
                    tool_message_builder._observation_builder
                )

            self._embodied_loop_helper = EmbodiedAgentLoopHelper(
                observation_builder=embodied_builder,
            )

    def run(
        self,
        context: "AgentContext",
        messages: list["Message"],
    ) -> "AgentResult":

        from app.agents.types import AgentResult

        collected_observations: list[Observation] = []

        for iteration in range(self._config.max_iterations):

            if self._config.enable_embodied:

                logger.info(
                    "Embodied Agent Loop iteration %d/%d",
                    iteration + 1,
                    self._config.max_iterations,
                )

            try:

                start = time.perf_counter()

                from app.monitoring.tokens import estimate_token_count

                prompt_text = "".join(
                    message.content or ""
                    for message in messages
                )

                prompt_tokens = estimate_token_count(
                    prompt_text
                )

                result = self._client.chat(messages)

                duration_ms = (
                    time.perf_counter() - start
                ) * 1000

                completion_tokens = estimate_token_count(
                    result.content or ""
                )

                self._tracer.on_llm_call(
                    model=result.model,
                    input_message_count=len(messages),
                    content_preview=(
                        result.content or ""
                    )[:200],
                    has_tool_calls=result.has_tool_calls,
                    tool_call_count=len(result.tool_calls),
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            except Exception as error:

                duration_ms = (
                    time.perf_counter() - start
                ) * 1000

                from app.monitoring.tokens import estimate_token_count

                prompt_text = "".join(
                    message.content or ""
                    for message in messages
                )

                self._tracer.on_llm_call(
                    model="",
                    input_message_count=len(messages),
                    duration_ms=duration_ms,
                    prompt_tokens=estimate_token_count(
                        prompt_text
                    ),
                    error=str(error),
                )

                return self._error_handler.handle_llm_error(
                    error
                )

            if not result.has_tool_calls:

                agent_result = AgentResult(
                    success=True,
                    model=result.model,
                    content=result.content or "",
                    observations=collected_observations,
                )

                self._tracer.on_final_answer(
                    agent_result
                )

                return agent_result

            tool_results = self._execute_tool_calls(
                result.tool_calls
            )

            if self._embodied_loop_helper is not None:

                round_observations = (
                    self._embodied_loop_helper.collect_observations(
                        result.tool_calls,
                        tool_results,
                    )
                )

                collected_observations.extend(
                    round_observations,
                )

                for observation in round_observations:

                    self._tracer.on_embodied_observation(
                        observation,
                        iteration=iteration + 1,
                    )

            round_messages = (
                self._tool_message_builder.build_tool_round(
                    result.tool_calls,
                    tool_results,
                    assistant_content=result.content,
                )
            )

            for message in round_messages:

                if message.role == "tool":

                    self._tracer.on_observation(
                        message
                    )

            messages.extend(round_messages)

        agent_result = AgentResult(
            success=False,
            model="",
            content=(
                "The agent exceeded the maximum number "
                "of tool-calling iterations."
            ),
            observations=collected_observations,
        )

        self._tracer.on_final_answer(
            agent_result
        )

        return agent_result

    def _execute_tool_calls(
        self,
        tool_calls,
    ) -> list[ToolResult]:

        tool_results: list[ToolResult] = []

        for tool_call in tool_calls:

            start = time.perf_counter()

            try:

                tool_result = self._tool_manager.execute(

                    ToolContext(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                    )

                )

            except Exception as error:

                duration_ms = (
                    time.perf_counter() - start
                ) * 1000

                tool_result = self._error_handler.handle_tool_error(
                    error,
                    tool_call.name,
                )

                self._tracer.on_tool_call(
                    tool_call,
                    output=tool_result.content,
                    success=tool_result.success,
                    duration_ms=duration_ms,
                    error=str(error),
                )

                tool_results.append(tool_result)

                continue

            duration_ms = (
                time.perf_counter() - start
            ) * 1000

            self._tracer.on_tool_call(
                tool_call,
                output=tool_result.content,
                success=tool_result.success,
                duration_ms=duration_ms,
                error=(
                    None
                    if tool_result.success
                    else tool_result.content
                ),
            )

            tool_results.append(tool_result)

        return tool_results
