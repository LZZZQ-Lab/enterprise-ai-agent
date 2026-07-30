from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.llm.base import BaseLLM
from app.llm.local_provider import LocalLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.vllm_provider import VLLMProvider
from app.model_registry.manager import reset_model_registry_manager
from app.router.engine import reset_router_engine

SUPPORTED_PROVIDERS = frozenset(
    {"openai", "local", "vllm", "sglang", "tgi", "gateway"},
)


def create_llm_provider(
    provider_name: str | None = None,
) -> BaseLLM:
    """
    根据配置创建 LLM Provider 实例。

    MODEL_PROVIDER=local 时返回 LocalLLMProvider，自动解析 Qwen 模型 ID。
    """

    app_settings = get_settings()

    name = (provider_name or app_settings.MODEL_PROVIDER).lower().strip()

    if app_settings.ENABLE_INFERENCE_GATEWAY and name != "gateway":
        from app.gateway.provider import GatewayLLMProvider

        return GatewayLLMProvider(provider_name=name)

    if name == "gateway":
        from app.gateway.provider import GatewayLLMProvider

        return GatewayLLMProvider(
            provider_name=app_settings.INFERENCE_BACKEND
            or app_settings.MODEL_PROVIDER,
        )

    if name == "openai":

        return OpenAIProvider()

    if name == "local":

        app_settings = get_settings()
        model_info = app_settings.resolve_model_info()
        return LocalLLMProvider(model_id=model_info.model_id)

    if name == "vllm":

        return VLLMProvider()

    if name == "sglang" or name == "tgi":
        from app.gateway.provider import GatewayLLMProvider

        return GatewayLLMProvider(provider_name=name)

    raise ValueError(
        f"Unknown LLM provider '{name}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
    )


@lru_cache
def get_llm_provider() -> BaseLLM:

    return create_llm_provider()


@lru_cache
def get_llm_client() -> BaseLLM:
    """
    向后兼容入口，返回当前配置的 Provider。

    Agent 通过本函数获取 LLM，切换 MODEL_PROVIDER 即可更换后端。
    """

    return get_llm_provider()


def reset_llm_client_cache() -> None:
    """
    清除 LLM Provider 单例缓存。

    修改 .env 或 Provider 实现后，若未重启 uvicorn，可主动调用。
    """

    get_llm_provider.cache_clear()
    get_llm_client.cache_clear()
    reset_model_registry_manager()
    reset_router_engine()

    from app.gateway.service import reset_inference_gateway
    from app.gateway.stats import reset_token_stats

    reset_inference_gateway()
    reset_token_stats()

    from app.gpu.manager import reset_gpu_resource_manager

    reset_gpu_resource_manager()

    from app.service.manager import reset_service_discovery_manager

    reset_service_discovery_manager()

    from app.cache.manager import reset_model_cache_manager
    from app.cache.stats import reset_cache_stats

    reset_model_cache_manager()
    reset_cache_stats()

    from app.llm.local.model_loader import ModelLoader

    ModelLoader.reset_cache()
