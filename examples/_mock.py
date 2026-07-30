"""Offline LLM stubs for examples/ demos — no API Key / GPU required."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from app.llm.base import BaseLLM
from app.llm.types import ChatResult
from app.llm.types import Message
from app.llm.types import ToolCall


@dataclass
class DemoChatLLM(BaseLLM):
    """Returns a fixed assistant reply for basic chat demos."""

    model: str = "demo-chat-mock"
    reply: str = (
        "你好！我是 Enterprise AI Platform 的 Mock LLM。"
        "当前运行在离线 Mock 模式，无需 API Key。"
    )

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        return ChatResult(
            model=self.model,
            content=f"{self.reply}\n\n（收到：{user[:80]}）",
        )


@dataclass
class DemoRAGLLM(BaseLLM):
    """Stub LLM for RAG ask() — echoes that context was injected."""

    model: str = "demo-rag-mock"
    reply: str = (
        "根据企业知识库，平台支持文档上传、向量检索与带来源引用的问答。"
    )
    last_messages: list[Message] = field(default_factory=list)

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        self.last_messages = list(messages)
        context_hits = sum(
            1
            for m in messages
            if m.role == "user" and "检索到的上下文" in (m.content or "")
        )
        suffix = (
            f" [Mock：Prompt 含 {len(messages)} 条消息"
            f"，检索上下文块≈{context_hits}]"
        )
        return ChatResult(
            model=self.model,
            content=self.reply + suffix,
        )


@dataclass
class DemoToolCallingLLM:
    """First turn: time tool; second turn: final answer."""

    model: str = "demo-agent-mock"
    tool_name: str = "time"
    final_content: str = "当前时间已通过 time 工具获取，Mock Agent Loop 完成。"
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
                        id="demo-call-1",
                        name=self.tool_name,
                        arguments={},
                    )
                ],
            )
        return ChatResult(
            model=self.model,
            content=self.final_content,
        )


@dataclass
class DemoGatewayBackend(BaseLLM):
    """Minimal backend for Inference Gateway infra demo."""

    model: str = "demo-gateway-model"

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        from app.gateway.types import TokenUsage

        self.last_usage = TokenUsage(
            prompt_tokens=12,
            completion_tokens=8,
            total_tokens=20,
        )
        return ChatResult(
            model=self.model,
            content="Gateway Mock 推理完成。",
        )
