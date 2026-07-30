from app.embodied.observation_factory import ObservationFactory
from app.embodied.types import ObservationType
from app.llm.types import Message
from app.agents.executor.observation_builder import ObservationBuilder
from app.tools.types import ToolResult


class EmbodiedObservationBuilder:
    """
    具身智能 Observation Builder。

    在保留原有 ObservationBuilder 行为的基础上，
    对 vision / robot 类 Tool 结果输出结构化 Observation 文本，
    供 Agent Loop 的 Reasoning 阶段继续推理。
    """

    def __init__(
        self,
        fallback_builder: ObservationBuilder | None = None,
    ) -> None:

        self._fallback_builder = (
            fallback_builder or ObservationBuilder()
        )

    def build(
        self,
        tool_result: ToolResult,
        *,
        tool_call_id: str,
        tool_name: str,
    ) -> Message:

        observation = ObservationFactory.from_tool_result(
            tool_result,
            tool_name=tool_name,
        )

        if observation.type in {
            ObservationType.VISION.value,
            ObservationType.ROBOT.value,
        }:

            content = observation.to_prompt_text()

        else:

            return self._fallback_builder.build(
                tool_result,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
            )

        return Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
        )

    def build_observation(
        self,
        tool_result: ToolResult,
        *,
        tool_name: str,
    ):
        """构建 Observation 对象，供 Agent Loop 收集。"""

        return ObservationFactory.from_tool_result(
            tool_result,
            tool_name=tool_name,
        )
