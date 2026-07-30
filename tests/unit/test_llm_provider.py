"""LLM Provider 测试。"""

from __future__ import annotations

import pytest

from app.config import settings
from app.llm.base import BaseLLM
from app.llm.factory import create_llm_provider
from app.llm.factory import get_llm_client
from app.llm.local_provider import LocalLLMProvider
from app.llm.local_provider import LocalProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.types import Message
from app.llm.vllm_provider import VLLMProvider


@pytest.fixture(autouse=True)
def _disable_inference_gateway_for_legacy_tests(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_INFERENCE_GATEWAY", "false")
    from app.config.settings import get_settings
    from app.llm.factory import reset_llm_client_cache

    get_settings.cache_clear()
    reset_llm_client_cache()


def test_base_llm_is_abstract() -> None:

    with pytest.raises(TypeError):

        BaseLLM()


def test_settings_exposes_model_provider() -> None:

    assert settings.MODEL_PROVIDER
    assert settings.MODEL_NAME


def test_create_openai_provider() -> None:

    provider = create_llm_provider("openai")

    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, BaseLLM)
    assert hasattr(provider, "chat")


def test_create_local_provider() -> None:

    provider = create_llm_provider("local")

    assert isinstance(provider, LocalLLMProvider)
    assert isinstance(provider, LocalProvider)
    assert isinstance(provider, BaseLLM)
    assert provider.model_id


def test_factory_uses_local_when_model_provider_local(monkeypatch) -> None:

    monkeypatch.setenv("MODEL_PROVIDER", "local")
    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")

    from app.config.settings import reset_settings_cache
    from app.config.settings import get_settings
    from app.llm.factory import reset_llm_client_cache

    get_settings.cache_clear()
    reset_llm_client_cache()

    provider = create_llm_provider()

    assert isinstance(provider, LocalLLMProvider)
    assert provider.model_id == "Qwen/Qwen2.5-0.5B-Instruct"


def test_resolve_local_model_id_from_model_name(monkeypatch) -> None:

    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")
    monkeypatch.setenv("LOCAL_MODEL_ID", "")

    from app.config.settings import Settings
    from app.config.settings import get_settings

    get_settings.cache_clear()
    loaded = Settings()

    assert loaded.resolve_local_model_id() == "Qwen/Qwen2.5-0.5B-Instruct"


def test_chat_agent_auto_selects_local_provider(monkeypatch) -> None:

    monkeypatch.setenv("MODEL_PROVIDER", "local")
    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")

    from app.agents.chat_agent import ChatAgent
    from app.config import AgentConfig
    from app.config.settings import reset_settings_cache
    from app.llm.factory import reset_llm_client_cache

    reset_settings_cache()
    reset_llm_client_cache()

    agent = ChatAgent(
        config=AgentConfig(
            max_iterations=1,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        ),
    )

    assert isinstance(agent.client, LocalLLMProvider)


def test_local_provider_chat_without_transformers() -> None:

    class FakeInference:

        model_id = "fake/Qwen2.5-0.5B-Instruct"

        def generate(
            self,
            messages,
            *,
            max_new_tokens=None,
            temperature=None,
        ) -> str:

            return "你好，我是 Qwen 本地助手。"

    provider = LocalLLMProvider(inference=FakeInference())

    result = provider.chat(
        [Message(role="user", content="你好，请介绍一下自己")],
        use_tools=False,
    )

    assert result.model == "fake/Qwen2.5-0.5B-Instruct"
    assert "Qwen" in (result.content or "")


def test_qwen_message_format() -> None:

    from app.llm.local.tokenizer import messages_to_chat_dicts

    chat = messages_to_chat_dicts(
        [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="你好"),
            Message(role="tool", content="result", name="time"),
        ]
    )

    assert chat[0]["role"] == "system"
    assert chat[1]["role"] == "user"
    assert chat[2]["role"] == "user"
    assert "Tool Result" in chat[2]["content"]


def test_create_vllm_provider() -> None:

    provider = create_llm_provider("vllm")

    assert isinstance(provider, VLLMProvider)
    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, BaseLLM)
    assert provider.model_id


def test_chat_agent_auto_selects_vllm_provider(monkeypatch) -> None:

    monkeypatch.setenv("MODEL_PROVIDER", "vllm")
    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")
    monkeypatch.setenv("VLLM_ENDPOINT", "http://127.0.0.1:8000/v1")

    from app.agents.chat_agent import ChatAgent
    from app.config import AgentConfig
    from app.config.settings import reset_settings_cache
    from app.llm.factory import reset_llm_client_cache

    reset_settings_cache()
    reset_llm_client_cache()

    agent = ChatAgent(
        config=AgentConfig(
            max_iterations=1,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        ),
    )

    assert isinstance(agent.client, VLLMProvider)
    assert agent.client.model_id == "Qwen/Qwen2.5-0.5B-Instruct"


def test_get_llm_client_backward_compat() -> None:

    from app.llm.client import LLMClient

    client = get_llm_client()

    assert isinstance(client, BaseLLM)
    assert LLMClient is OpenAIProvider


def test_openai_tool_argument_recovery() -> None:

    broken = '{"path": "D:\\\\tmp\\\\a.txt", "content": "hello'

    args = OpenAIProvider._parse_arguments("write_file", broken)

    assert args["path"] == "D:\\tmp\\a.txt"
    assert args["content"] == "hello"
