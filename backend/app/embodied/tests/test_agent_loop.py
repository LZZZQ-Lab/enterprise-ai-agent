"""
Task13.6 Agent Loop 升级测试。

运行:
    cd backend
    python -m app.embodied.tests.test_agent_loop
"""

from __future__ import annotations

from app.agents.types import AgentContext
from app.embodied.embodied_observation_builder import EmbodiedObservationBuilder
from app.llm.types import ChatResult
from app.llm.types import ToolCall
from app.agents.executor.agent_executor import AgentExecutor
from app.config import AgentConfig
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.tools.factory import ToolFactory
from app.tools.manager import ToolManager
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class MockLLMClient:
    """用于测试 Agent Loop 的 Mock LLM。"""

    def __init__(
        self,
        responses: list[ChatResult],
    ) -> None:

        self._responses = responses
        self._index = 0
        self.messages_history: list = []

    def bind_tool_manager(
        self,
        tool_manager: ToolManager,
    ) -> None:

        return None

    def chat(
        self,
        messages,
    ) -> ChatResult:

        self.messages_history.append(list(messages))

        if self._index >= len(self._responses):

            return ChatResult(
                model="mock",
                content="fallback answer",
            )

        result = self._responses[self._index]
        self._index += 1

        return result


def _build_executor(
    *,
    enable_embodied: bool,
    max_iterations: int,
    responses: list[ChatResult],
) -> AgentExecutor:

    ToolFactory._initialized = False
    ToolFactory.initialize()

    config = AgentConfig(
        enable_embodied=enable_embodied,
        max_iterations=max_iterations,
    )

    embodied_builder = EmbodiedObservationBuilder()
    tool_message_builder = ToolMessageBuilder(
        observation_builder=embodied_builder,
    )

    return AgentExecutor(
        client=MockLLMClient(responses),
        config=config,
        tool_message_builder=tool_message_builder,
        tool_manager=ToolManager(config=config),
        error_handler=AgentErrorHandler(),
        tracer=AgentTracer(),
    )


def test_embodied_loop_action_observation_reasoning_cycle() -> None:

    responses = [
        ChatResult(
            model="mock",
            content="我先观察环境。",
            tool_calls=[
                ToolCall(
                    id="call-vision-1",
                    name="analyze_image",
                    arguments={
                        "image": "mock-image",
                        "prompt": "找红色杯子",
                    },
                ),
            ],
        ),
        ChatResult(
            model="mock",
            content="我去抓取杯子。",
            tool_calls=[
                ToolCall(
                    id="call-robot-1",
                    name="robot_grasp",
                    arguments={"target": "red cup"},
                ),
            ],
        ),
        ChatResult(
            model="mock",
            content="任务完成，已拿到红色杯子。",
        ),
    ]

    executor = _build_executor(
        enable_embodied=True,
        max_iterations=5,
        responses=responses,
    )

    result = executor.run(
        AgentContext(
            session_id="test-session",
            user_message="帮我拿桌上的红色杯子",
        ),
        messages=[],
    )

    assert result.success is True
    assert "任务完成" in result.content
    assert len(result.observations) == 2
    assert result.observations[0].type == "vision"
    assert result.observations[1].type == "robot"
    assert "red cup" in result.observations[1].content

    robot_tool_messages = [
        message
        for history in executor._client.messages_history
        for message in history
        if (
            message.role == "tool"
            and message.content.startswith(
                "[Observation:robot:success]"
            )
        )
    ]

    assert len(robot_tool_messages) == 1


def test_legacy_loop_without_embodied_flag() -> None:

    responses = [
        ChatResult(
            model="mock",
            content="",
            tool_calls=[
                ToolCall(
                    id="call-time-1",
                    name="time",
                    arguments={},
                ),
            ],
        ),
        ChatResult(
            model="mock",
            content="now is available",
        ),
    ]

    executor = _build_executor(
        enable_embodied=False,
        max_iterations=5,
        responses=responses,
    )

    result = executor.run(
        AgentContext(
            session_id="test-session",
            user_message="现在几点",
        ),
        messages=[],
    )

    assert result.success is True
    assert result.observations == []

    tool_messages = [
        message
        for message in executor._client.messages_history[-1]
        if message.role == "tool"
    ]

    assert len(tool_messages) == 1
    assert not tool_messages[0].content.startswith(
        "[Observation:"
    )


def test_max_iterations_prevents_infinite_loop() -> None:

    infinite_tool_calls = ChatResult(
        model="mock",
        content="继续调用工具",
        tool_calls=[
            ToolCall(
                id="call-loop",
                name="time",
                arguments={},
            ),
        ],
    )

    executor = _build_executor(
        enable_embodied=True,
        max_iterations=2,
        responses=[infinite_tool_calls, infinite_tool_calls, infinite_tool_calls],
    )

    result = executor.run(
        AgentContext(
            session_id="test-session",
            user_message="loop test",
        ),
        messages=[],
    )

    assert result.success is False
    assert "maximum number" in result.content
    assert len(result.observations) == 2


def test_embodied_observation_builder_formats_vision_and_tool() -> None:

    builder = EmbodiedObservationBuilder()

    vision_tool = ToolManager().execute(
        ToolContext(
            tool_name="analyze_image",
            arguments={
                "image": "mock-image",
                "prompt": "找红色杯子",
            },
        )
    )

    vision_message = builder.build(
        vision_tool,
        tool_call_id="call-1",
        tool_name="analyze_image",
    )

    assert vision_message.content.startswith(
        "[Observation:vision:success]"
    )

    plain_message = builder.build(
        ToolResult(
            success=True,
            content="2026-07-22 12:00:00",
        ),
        tool_call_id="call-2",
        tool_name="time",
    )

    assert plain_message.content == "2026-07-22 12:00:00"


def run_all_tests() -> None:

    test_embodied_loop_action_observation_reasoning_cycle()
    test_legacy_loop_without_embodied_flag()
    test_max_iterations_prevents_infinite_loop()
    test_embodied_observation_builder_formats_vision_and_tool()

    print("Task13.6 Agent Loop tests passed.")


if __name__ == "__main__":

    run_all_tests()
