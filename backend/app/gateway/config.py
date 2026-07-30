"""
解析 Inference Gateway 后端配置（含服务发现 Failover）。
"""

from __future__ import annotations

from app.config.settings import Settings
from app.config.settings import get_settings
from app.gateway.backends.local import LocalInferenceBackend
from app.gateway.backends.openai_compat import OpenAICompatBackend
from app.gateway.types import InferenceBackendKind
from app.llm.base import BaseLLM


def resolve_backend_kind(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> InferenceBackendKind:
    app = settings or get_settings()
    raw = (provider_name or app.INFERENCE_BACKEND or app.MODEL_PROVIDER)
    raw = raw.lower().strip()
    try:
        return InferenceBackendKind(raw)
    except ValueError as exc:
        raise ValueError(
            f"Unknown inference backend '{raw}'. "
            f"Supported: {', '.join(k.value for k in InferenceBackendKind)}"
        ) from exc


def create_inference_backend(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> BaseLLM:
    app = settings or get_settings()
    kind = resolve_backend_kind(provider_name, app)

    if kind == InferenceBackendKind.LOCAL:
        return LocalInferenceBackend()

    if kind == InferenceBackendKind.OPENAI:
        return OpenAICompatBackend(
            backend_kind=kind,
            api_key=app.API_KEY,
            base_url=app.OPENAI_BASE_URL,
        )

    if kind == InferenceBackendKind.VLLM:
        return _create_discovered_or_static(
            kind=kind,
            app=app,
            static_url=app.VLLM_ENDPOINT.rstrip("/"),
            static_key=app.VLLM_API_KEY or app.API_KEY or "EMPTY",
            max_tokens=app.VLLM_MAX_TOKENS,
        )

    if kind == InferenceBackendKind.SGLANG:
        return _create_discovered_or_static(
            kind=kind,
            app=app,
            static_url=app.SGLANG_ENDPOINT.rstrip("/"),
            static_key=app.SGLANG_API_KEY or "EMPTY",
            max_tokens=app.SGLANG_MAX_TOKENS,
        )

    if kind == InferenceBackendKind.TGI:
        return OpenAICompatBackend(
            backend_kind=kind,
            api_key=app.TGI_API_KEY or "EMPTY",
            base_url=app.TGI_ENDPOINT.rstrip("/"),
            max_tokens=app.TGI_MAX_TOKENS,
        )

    raise ValueError(f"Unsupported backend: {kind}")


def _create_discovered_or_static(
    *,
    kind: InferenceBackendKind,
    app: Settings,
    static_url: str,
    static_key: str,
    max_tokens: int,
) -> BaseLLM:
    if app.ENABLE_SERVICE_DISCOVERY:
        node = _resolve_service_node(kind)
        if node is not None:
            return OpenAICompatBackend(
                backend_kind=kind,
                api_key=node.api_key,
                base_url=node.base_url.rstrip("/"),
                max_tokens=max_tokens,
                service_node_id=node.node_id,
            )

    return OpenAICompatBackend(
        backend_kind=kind,
        api_key=static_key,
        base_url=static_url,
        max_tokens=max_tokens,
    )


def _resolve_service_node(kind: InferenceBackendKind):
    from app.service.manager import get_service_discovery_manager
    from app.service.types import ProviderKind

    mapping = {
        InferenceBackendKind.VLLM: ProviderKind.VLLM,
        InferenceBackendKind.SGLANG: ProviderKind.SGLANG,
    }
    provider_kind = mapping.get(kind)
    if provider_kind is None:
        return None
    return get_service_discovery_manager().resolve_node(provider_kind)
