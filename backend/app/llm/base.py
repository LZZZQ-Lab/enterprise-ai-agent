from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Generator

from app.llm.types import ChatResult
from app.llm.types import Message
from app.tools.registry import ToolRegistry


class BaseLLM(ABC):
    """
    LLM Provider 统一接口。

    Agent 只依赖 chat()，不感知底层 OpenAI / Local / vLLM 实现。
    """

    def __init__(self) -> None:

        self._tool_manager = None

    def bind_tool_manager(
        self,
        tool_manager,
    ) -> None:
        """
        绑定 ToolManager，统一获取本地 + MCP Tool Schema。
        """

        self._tool_manager = tool_manager

    def _get_tool_schemas(self) -> list[dict]:

        if self._tool_manager is not None:

            return self._tool_manager.get_schemas()

        return ToolRegistry.get_schemas()

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        """
        发送消息并返回模型响应。
        """

    def stream_chat(
        self,
        messages: list[Message],
    ) -> Generator[str, None, None]:
        """
        流式输出，默认由具体 Provider 实现。
        """

        raise NotImplementedError(
            f"{type(self).__name__} does not support stream_chat."
        )
