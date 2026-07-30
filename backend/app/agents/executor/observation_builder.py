from app.llm.types import Message
from app.tools.types import ToolResult


class ObservationBuilder:
    """
    将 ToolResult 转换为 LLM 可消费的 Observation Message。

    单一职责：Tool 执行结果 → Message 的格式转换。
    兼容 OpenAI Tool Calling Protocol（role=tool）。
    """

    def build(
        self,
        tool_result: ToolResult,
        *,
        tool_call_id: str,
        tool_name: str,
    ) -> Message:

        return Message(
            role=self._resolve_role(),
            content=self._format_content(tool_result),
            tool_call_id=tool_call_id,
            name=tool_name,
        )

    def _resolve_role(self) -> str:

        return "tool"

    def _format_content(
        self,
        tool_result: ToolResult,
    ) -> str:

        if tool_result.success:

            return tool_result.content

        return f"[Tool Error] {tool_result.content}"
