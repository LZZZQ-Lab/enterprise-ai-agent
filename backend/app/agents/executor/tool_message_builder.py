from app.llm.types import Message
from app.llm.types import ToolCall
from app.agents.executor.observation_builder import ObservationBuilder
from app.tools.types import ToolResult


class ToolMessageBuilder:
    """
    统一构建 Tool Calling 相关 Message。

    Assistant Tool Call → Tool Message → Observation
    """

    def __init__(
        self,
        observation_builder: ObservationBuilder | None = None,
    ):

        self._observation_builder = (
            observation_builder or ObservationBuilder()
        )

    def build_assistant_tool_call(
        self,
        tool_calls: list[ToolCall],
        content: str | None = None,
    ) -> Message:

        return Message(
            role="assistant",
            content=content or "",
            tool_calls=tool_calls,
        )

    def build_tool_round(
        self,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
        *,
        assistant_content: str | None = None,
    ) -> list[Message]:
        """
        构建一轮 Tool Calling 所需的全部 Message。

        1 条 assistant(tool_calls) + N 条 tool observation
        """

        messages: list[Message] = [
            self.build_assistant_tool_call(
                tool_calls,
                content=assistant_content,
            )
        ]

        for tool_call, tool_result in zip(
            tool_calls,
            tool_results,
            strict=True,
        ):

            messages.append(
                self._observation_builder.build(
                    tool_result,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                )
            )

        return messages
