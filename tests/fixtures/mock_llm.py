"""LLM test doubles for Agent / Gateway unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from app.llm.types import ChatResult
from app.llm.types import ToolCall


@dataclass
class MockLLM:
    """Minimal LLM client stub."""

    model: str = "mock"
    content: str = "mock response"
    tool_calls: list[ToolCall] | None = None

    def bind_tool_manager(self, tool_manager) -> None:
        return None

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        return ChatResult(
            model=self.model,
            content=self.content,
            tool_calls=self.tool_calls,
        )


@dataclass
class MockLLMWithToolCall:
    """Returns tool_calls on first turn, text on subsequent turns."""

    model: str = "mock"
    tool_name: str = "time"
    tool_arguments: dict = field(default_factory=dict)
    final_content: str = "done"
    _turn: int = 0

    def bind_tool_manager(self, tool_manager) -> None:
        return None

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        self._turn += 1

        if self._turn == 1 and use_tools:
            return ChatResult(
                model=self.model,
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name=self.tool_name,
                        arguments=self.tool_arguments or {},
                    )
                ],
            )

        return ChatResult(
            model=self.model,
            content=self.final_content,
        )
