"""LLM Provider 从 Model Registry 解析模型与默认 max_tokens。"""

from __future__ import annotations

from app.model_registry.manager import get_model_registry_manager
from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor


def resolve_llm_model(
    model_name: str | None,
    *,
    default_name: str,
) -> ModelInfo:
    """
    将配置中的 MODEL_NAME / 传入 model_name 解析为 ModelInfo。
    """

    raw = (model_name or default_name or "").strip()
    if not raw:
        raise ValueError("Model name is required")

    manager = get_model_registry_manager()
    try:
        return manager.resolve(raw)
    except KeyError:
        ephemeral = ModelInfo(
            name=_ephemeral_name(raw),
            model_id=raw,
            provider=_infer_vendor(raw),
            context_length=128000,
            max_tokens=8192,
            capabilities=["chat"],
            aliases=[raw],
        )
        manager.register(ephemeral, overwrite=True)
        return ephemeral


def effective_max_tokens(
    *,
    explicit: int | None,
    settings_default: int,
    model_info: ModelInfo,
) -> int:
    """
    explicit 参数优先，其次 settings，最后不超过模型 max_tokens 上限。
    """

    chosen = explicit if explicit is not None else settings_default
    return min(chosen, model_info.max_tokens)


def _ephemeral_name(model_id: str) -> str:
    safe = model_id.replace("/", "-").replace(":", "-")
    return f"custom-{safe}"[:120]


def _infer_vendor(model_id: str) -> ModelVendor:
    lower = model_id.lower()
    if (
        lower.startswith("gpt-")
        or lower.startswith("o1")
        or lower.startswith("o3")
    ):
        return ModelVendor.OPENAI
    if "qwen" in lower:
        return ModelVendor.QWEN
    if "deepseek" in lower:
        return ModelVendor.DEEPSEEK
    if "llama" in lower or "meta-llama" in lower:
        return ModelVendor.LLAMA
    return ModelVendor.OPENAI
