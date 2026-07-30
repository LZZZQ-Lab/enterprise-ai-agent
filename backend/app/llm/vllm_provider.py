from __future__ import annotations

from app.config.settings import get_settings
from app.core.logger import logger
from app.llm.openai_provider import OpenAIProvider


def apply_vllm_tool_calling_policy(
    use_tools: bool,
    tool_schemas: list[dict],
) -> bool:
    """
    vLLM 默认不发送 tools；仅在 VLLM_ENABLE_TOOL_CALLING=true
    且服务已配置 --enable-auto-tool-choice 时启用。
    """

    if use_tools and not get_settings().VLLM_ENABLE_TOOL_CALLING:

        if tool_schemas:

            logger.warning(
                "vLLM tool calling disabled "
                "(set VLLM_ENABLE_TOOL_CALLING=true and start vLLM with "
                "--enable-auto-tool-choice --tool-call-parser qwen); "
                "tools omitted for this request."
            )

        return False

    return use_tools


class VLLMProvider(OpenAIProvider):
    """
    vLLM OpenAI Compatible API Provider（Task 2.5）。

    通过 HTTP 调用 vLLM 服务的 /v1/chat/completions，底层模型通常为 Qwen2.5-Instruct。
    Agent 仅通过 get_llm_client() 调用，不感知 vLLM 部署细节。
    """

    def __init__(self) -> None:

        app_settings = get_settings()

        super().__init__(
            api_key=app_settings.VLLM_API_KEY or app_settings.API_KEY or "EMPTY",
            base_url=app_settings.VLLM_ENDPOINT.rstrip("/"),
            model_name=app_settings.MODEL_NAME,
            max_tokens=app_settings.VLLM_MAX_TOKENS,
        )

        self.endpoint = app_settings.VLLM_ENDPOINT.rstrip("/")

        logger.info(
            "VLLMProvider initialized: endpoint=%s model=%s provider=vllm",
            self.endpoint,
            self.model_id,
        )

    def _resolve_use_tools(self, use_tools: bool) -> bool:

        return apply_vllm_tool_calling_policy(
            use_tools,
            self._get_tool_schemas(),
        )


__all__ = ["VLLMProvider", "apply_vllm_tool_calling_policy"]
