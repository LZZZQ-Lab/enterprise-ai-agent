"""
OpenAI 兼容 HTTP 后端（OpenAI / vLLM / SGLang / TGI）。
"""

from __future__ import annotations

from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage
from app.llm.openai_provider import OpenAIProvider


class OpenAICompatBackend(OpenAIProvider):
    """
    基于 OpenAI SDK 的兼容后端，并暴露 last_usage 供网关统计。
    """

    def __init__(
        self,
        *,
        backend_kind: InferenceBackendKind,
        api_key: str,
        base_url: str,
        model_name: str | None = None,
        max_tokens: int | None = None,
        service_node_id: str | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            max_tokens=max_tokens,
        )
        self.backend_kind = backend_kind
        self.service_node_id = service_node_id
        self._last_usage = TokenUsage()

    def _resolve_use_tools(self, use_tools: bool) -> bool:

        if self.backend_kind == InferenceBackendKind.VLLM:

            from app.llm.vllm_provider import apply_vllm_tool_calling_policy

            return apply_vllm_tool_calling_policy(
                use_tools,
                self._get_tool_schemas(),
            )

        return use_tools

    @property
    def last_usage(self) -> TokenUsage:
        return self._last_usage

    def _create_completion_with_retry(self, request_kwargs: dict):
        response = super()._create_completion_with_retry(request_kwargs)
        self._last_usage = TokenUsage.from_openai_usage(
            getattr(response, "usage", None),
        )
        return response
