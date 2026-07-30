"""
本地推理后端（transformers）。
"""

from __future__ import annotations

from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage
from app.llm.base import BaseLLM
from app.llm.local_provider import LocalLLMProvider
from app.llm.types import ChatResult
from app.llm.types import Message


class LocalInferenceBackend(BaseLLM):
    """将 LocalLLMProvider 适配为网关后端。"""

    backend_kind = InferenceBackendKind.LOCAL

    def __init__(self, provider: LocalLLMProvider | None = None) -> None:
        super().__init__()
        from app.config.settings import get_settings
        from app.model_registry.provider_bridge import resolve_llm_model

        app_settings = get_settings()
        model_info = resolve_llm_model(
            None,
            default_name=app_settings.MODEL_NAME,
        )
        self._model_info = model_info
        self._provider = provider or LocalLLMProvider(
            model_id=model_info.model_id,
        )
        self._last_usage = TokenUsage()

    @property
    def model_id(self) -> str:
        return self._provider.model_id

    @property
    def model_info(self):
        return self._model_info

    @property
    def last_usage(self) -> TokenUsage:
        return self._last_usage

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        if self._tool_manager is not None:
            self._provider.bind_tool_manager(self._tool_manager)

        prompt_text = " ".join(
            (message.content or "")
            for message in messages
        )
        result = self._provider.chat(messages, use_tools=use_tools)
        completion = result.content or ""
        self._last_usage = TokenUsage.estimate_from_text(
            prompt_text,
            completion,
        )
        return result
