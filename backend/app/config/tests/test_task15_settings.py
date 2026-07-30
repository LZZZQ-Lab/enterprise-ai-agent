"""
Task 1.5 企业级配置管理测试。

运行:
    cd backend
    python -m app.config.tests.test_task15_settings
"""

from __future__ import annotations

import os
from unittest.mock import patch

from app.config import AgentConfig
from app.config import Settings
from app.config import get_settings
from app.config import settings


def test_settings_loads_from_env() -> None:

    assert settings.APP_NAME
    assert settings.MODEL_PROVIDER
    assert settings.MODEL_NAME
    assert settings.MAX_AGENT_LOOP >= 1
    assert isinstance(settings.API_KEY, str)


def test_settings_alias_backward_compat() -> None:

    assert settings.LLM_PROVIDER == settings.MODEL_PROVIDER
    assert settings.OPENAI_API_KEY == settings.API_KEY


def test_agent_config_from_env() -> None:

    from app.config.settings import get_settings

    app_settings = get_settings()
    config = AgentConfig.from_env()

    assert config.max_iterations == app_settings.MAX_AGENT_LOOP
    assert config.temperature == app_settings.TEMPERATURE
    assert config.planner_model == app_settings.MODEL_NAME


def test_agent_config_from_env_overrides() -> None:

    config = AgentConfig.from_env(
        enable_multi_agent=True,
        max_iterations=3,
    )

    assert config.enable_multi_agent is True
    assert config.max_iterations == 3


def test_model_provider_alias_from_env_var() -> None:

    with patch.dict(os.environ, {"LLM_PROVIDER": "local"}, clear=False):

        get_settings.cache_clear()
        loaded = Settings()

        assert loaded.MODEL_PROVIDER == "local"

    get_settings.cache_clear()


def test_api_key_alias_from_env_var() -> None:

    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "sk-test-key"},
        clear=False,
    ):

        get_settings.cache_clear()
        loaded = Settings()

        assert loaded.API_KEY == "sk-test-key"

    get_settings.cache_clear()


def test_llm_factory_reads_model_provider() -> None:

    from app.llm.factory import create_llm_provider
    from app.llm.local_provider import LocalProvider
    from app.llm.openai_provider import OpenAIProvider
    from app.llm.vllm_provider import VLLMProvider

    assert isinstance(create_llm_provider("openai"), OpenAIProvider)
    assert isinstance(create_llm_provider("local"), LocalProvider)
    assert isinstance(create_llm_provider("vllm"), VLLMProvider)


def run_all_tests() -> None:

    test_settings_loads_from_env()
    test_settings_alias_backward_compat()
    test_agent_config_from_env()
    test_agent_config_from_env_overrides()
    test_model_provider_alias_from_env_var()
    test_api_key_alias_from_env_var()
    test_llm_factory_reads_model_provider()

    print("Task 1.5 settings tests passed.")


if __name__ == "__main__":

    run_all_tests()
