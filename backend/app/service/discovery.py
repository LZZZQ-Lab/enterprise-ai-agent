"""
从 Settings 自动发现 vLLM / SGLang 节点。
"""

from __future__ import annotations

from app.config.settings import Settings
from app.config.settings import get_settings
from app.service.registry import ProviderRegistry
from app.service.types import ProviderKind
from app.service.types import ProviderRegisterRequest


def bootstrap_providers(
    registry: ProviderRegistry,
    settings: Settings | None = None,
    *,
    overwrite: bool = False,
) -> int:
    """
    解析 ``VLLM_NODES`` / ``SGLANG_NODES`` 与环境默认 endpoint。
    """

    app = settings or get_settings()
    count = 0

    for url in _parse_node_list(app.VLLM_NODES):
        count += _register_url(
            registry,
            kind=ProviderKind.VLLM,
            base_url=url,
            api_key=app.VLLM_API_KEY or app.API_KEY or "EMPTY",
            overwrite=overwrite,
        )

    if not _parse_node_list(app.VLLM_NODES) and app.VLLM_ENDPOINT.strip():
        count += _register_url(
            registry,
            kind=ProviderKind.VLLM,
            base_url=app.VLLM_ENDPOINT,
            api_key=app.VLLM_API_KEY or app.API_KEY or "EMPTY",
            node_id="vllm-default",
            overwrite=True,
        )

    for url in _parse_node_list(app.SGLANG_NODES):
        count += _register_url(
            registry,
            kind=ProviderKind.SGLANG,
            base_url=url,
            api_key=app.SGLANG_API_KEY or "EMPTY",
            overwrite=overwrite,
        )

    if not _parse_node_list(app.SGLANG_NODES) and app.SGLANG_ENDPOINT.strip():
        count += _register_url(
            registry,
            kind=ProviderKind.SGLANG,
            base_url=app.SGLANG_ENDPOINT,
            api_key=app.SGLANG_API_KEY or "EMPTY",
            node_id="sglang-default",
            overwrite=True,
        )

    return count


def _parse_node_list(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _register_url(
    registry: ProviderRegistry,
    *,
    kind: ProviderKind,
    base_url: str,
    api_key: str,
    node_id: str | None = None,
    overwrite: bool = False,
) -> int:
    request = ProviderRegisterRequest(
        node_id=node_id,
        kind=kind,
        base_url=base_url,
        api_key=api_key,
    )
    try:
        registry.register(request, overwrite=overwrite)
    except ValueError:
        if overwrite:
            registry.register(request, overwrite=True)
        else:
            return 0
    return 1
