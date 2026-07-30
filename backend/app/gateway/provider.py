"""
GatewayLLMProvider：Agent 统一经 Inference Gateway 调用推理。
"""

from __future__ import annotations

from collections.abc import Generator

from app.config.settings import get_settings
from app.gateway.service import InferenceGateway
from app.gateway.types import GatewayCallMeta
from app.llm.base import BaseLLM
from app.llm.types import ChatResult
from app.llm.types import Message
from app.model_registry.provider_bridge import resolve_llm_model


class GatewayLLMProvider(BaseLLM):
    """
    实现 BaseLLM，内部委托 InferenceGateway。
    """

    def __init__(
        self,
        *,
        provider_name: str | None = None,
        gateway: InferenceGateway | None = None,
    ) -> None:
        super().__init__()

        app_settings = get_settings()
        self._provider_name = (
            provider_name or app_settings.MODEL_PROVIDER
        ).lower().strip()
        self._gateway = gateway or InferenceGateway(
            provider_name=self._provider_name,
        )
        self._model_info = resolve_llm_model(
            None,
            default_name=app_settings.MODEL_NAME,
        )
        self._last_meta: GatewayCallMeta | None = None
        self._last_routing_report = None

    @property
    def model_info(self):
        return self._model_info

    @property
    def model_id(self) -> str:
        backend = self._gateway.backend
        return getattr(backend, "model_id", self._model_info.model_id)

    @property
    def last_gateway_meta(self) -> GatewayCallMeta | None:
        return self._last_meta

    @property
    def last_routing_report(self):
        backend = self._gateway.backend
        return getattr(backend, "last_routing_report", None)

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        if self._tool_manager is not None:
            self._gateway.bind_tool_manager(self._tool_manager)

        payload = self._gateway.chat(
            messages,
            use_tools=use_tools,
        )
        self._last_meta = payload.meta
        return payload.result

    def stream_chat(
        self,
        messages: list[Message],
    ) -> Generator[str, None, None]:
        backend = self._gateway.backend
        if self._tool_manager is not None:
            backend.bind_tool_manager(self._tool_manager)
        yield from backend.stream_chat(messages)
