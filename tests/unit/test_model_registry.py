"""Task 7.1 Model Registry 测试。"""

from __future__ import annotations

import pytest

from app.model_registry.loader import DEFAULT_MODELS_FILE
from app.model_registry.loader import load_models_from_yaml
from app.model_registry.manager import ModelRegistryManager
from app.model_registry.models import ModelCost
from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor
from app.model_registry.repository import ModelRegistryRepository


def test_load_default_yaml_covers_vendors() -> None:
    models = load_models_from_yaml(DEFAULT_MODELS_FILE)
    vendors = {m.provider for m in models}
    assert ModelVendor.OPENAI in vendors
    assert ModelVendor.QWEN in vendors
    assert ModelVendor.DEEPSEEK in vendors
    assert ModelVendor.LLAMA in vendors


def test_resolve_qwen_alias() -> None:
    repo = ModelRegistryRepository()
    manager = ModelRegistryManager(
        repository=repo,
        auto_load=True,
    )
    info = manager.resolve("Qwen2.5")
    assert info.provider == ModelVendor.QWEN
    assert info.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert info.context_length >= 32768
    assert "chat" in info.capabilities


def test_dynamic_register_and_query() -> None:
    repo = ModelRegistryRepository()
    manager = ModelRegistryManager(repository=repo, auto_load=False)
    custom = ModelInfo(
        name="my-deepseek",
        model_id="deepseek-chat",
        provider=ModelVendor.DEEPSEEK,
        context_length=65536,
        max_tokens=4096,
        cost=ModelCost(input_per_1m=0.1, output_per_1m=0.2),
        capabilities=["chat", "code"],
        aliases=["ds-custom"],
    )
    manager.register(custom)
    assert manager.get("my-deepseek").cost.input_per_1m == 0.1
    listed = manager.query(provider=ModelVendor.DEEPSEEK)
    assert any(m.name == "my-deepseek" for m in listed)
    assert manager.resolve("ds-custom").name == "my-deepseek"


def test_register_duplicate_raises() -> None:
    repo = ModelRegistryRepository()
    manager = ModelRegistryManager(repository=repo, auto_load=False)
    model = ModelInfo(
        name="dup",
        model_id="gpt-test",
        provider=ModelVendor.OPENAI,
        context_length=8192,
        max_tokens=1024,
    )
    manager.register(model)
    with pytest.raises(ValueError):
        manager.register(model)


def test_settings_resolve_uses_registry(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_NAME", "deepseek-chat")
    monkeypatch.setenv("LOCAL_MODEL_ID", "")

    from app.config.settings import Settings
    from app.config.settings import get_settings
    from app.llm.factory import reset_llm_client_cache
    from app.model_registry.manager import reset_model_registry_manager

    get_settings.cache_clear()
    reset_llm_client_cache()
    reset_model_registry_manager()

    loaded = Settings()
    info = loaded.resolve_model_info()
    assert info.provider == ModelVendor.DEEPSEEK
    assert info.model_id == "deepseek-chat"
    assert loaded.resolve_vllm_model_id() == "deepseek-chat"


def test_openai_provider_uses_registry_model_id(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")
    monkeypatch.setenv("MODEL_PROVIDER", "openai")

    from app.config.settings import get_settings
    from app.llm.factory import reset_llm_client_cache
    from app.llm.openai_provider import OpenAIProvider
    from app.model_registry.manager import reset_model_registry_manager

    get_settings.cache_clear()
    reset_llm_client_cache()
    reset_model_registry_manager()

    provider = OpenAIProvider()
    assert provider.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert provider.model_info.provider == ModelVendor.QWEN
