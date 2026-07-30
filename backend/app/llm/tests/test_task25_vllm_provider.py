"""
Task 2.5 vLLM Provider 测试。

验证 openai / local / vllm 三种 Provider 可通过 MODEL_PROVIDER 切换，
且 ChatAgent 无需修改即可自动选择对应后端。

运行:
    cd backend
    pytest app/llm/tests/test_task25_vllm_provider.py -v
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.agents.chat_agent import ChatAgent
from app.config import AgentConfig
from app.config.settings import Settings
from app.config.settings import reset_settings_cache
from app.llm.base import BaseLLM
from app.llm.factory import create_llm_provider
from app.llm.factory import reset_llm_client_cache
from app.llm.local_provider import LocalLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.types import Message
from app.llm.vllm_provider import VLLMProvider
from app.gateway.backends.openai_compat import OpenAICompatBackend
from app.gateway.types import InferenceBackendKind


@pytest.fixture(autouse=True)
def _cleanup_provider_caches(monkeypatch) -> None:
    """避免 monkeypatch 污染后续测试的 Settings 缓存。"""

    monkeypatch.setenv("ENABLE_INFERENCE_GATEWAY", "false")

    yield

    reset_settings_cache()
    reset_llm_client_cache()


def _reset_provider_env(monkeypatch, **env: str) -> None:

    env.setdefault("ENABLE_INFERENCE_GATEWAY", "false")

    for key, value in env.items():

        monkeypatch.setenv(key, value)

    reset_settings_cache()
    reset_llm_client_cache()


def test_factory_creates_vllm_provider() -> None:

    provider = create_llm_provider("vllm")

    assert isinstance(provider, VLLMProvider)
    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, BaseLLM)
    assert provider.endpoint.endswith("/v1")
    assert provider.model_id


def test_resolve_vllm_model_id_from_alias(monkeypatch) -> None:

    monkeypatch.setenv("MODEL_NAME", "Qwen2.5")

    reset_settings_cache()

    loaded = Settings()

    assert loaded.resolve_vllm_model_id() == "Qwen/Qwen2.5-0.5B-Instruct"


def test_vllm_provider_uses_endpoint_and_model(monkeypatch) -> None:

    monkeypatch.setenv("VLLM_ENDPOINT", "http://127.0.0.1:9000/v1")
    monkeypatch.setenv("MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

    _reset_provider_env(monkeypatch)

    provider = create_llm_provider("vllm")

    assert provider.endpoint == "http://127.0.0.1:9000/v1"
    assert provider.model_id == "Qwen/Qwen2.5-1.5B-Instruct"
    assert str(provider.client.base_url).rstrip("/") == "http://127.0.0.1:9000/v1"


def test_vllm_provider_mock_chat(monkeypatch) -> None:

    _reset_provider_env(
        monkeypatch,
        MODEL_PROVIDER="vllm",
        VLLM_ENDPOINT="http://127.0.0.1:8000/v1",
        MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
    )

    provider = create_llm_provider("vllm")

    mock_response = SimpleNamespace(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="你好，我是 Qwen vLLM 助手。",
                    tool_calls=None,
                )
            )
        ],
    )

    provider.client = MagicMock()
    provider.client.chat.completions.create.return_value = mock_response

    result = provider.chat(
        [Message(role="user", content="你好")],
        use_tools=False,
    )

    assert result.content == "你好，我是 Qwen vLLM 助手。"
    assert result.model == "Qwen/Qwen2.5-0.5B-Instruct"

    call_kwargs = provider.client.chat.completions.create.call_args.kwargs

    assert call_kwargs["model"] == "Qwen/Qwen2.5-0.5B-Instruct"


def test_vllm_provider_omits_tools_by_default(monkeypatch) -> None:

    _reset_provider_env(
        monkeypatch,
        MODEL_PROVIDER="vllm",
        VLLM_ENDPOINT="http://127.0.0.1:8000/v1",
        MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        VLLM_ENABLE_TOOL_CALLING="false",
    )

    provider = create_llm_provider("vllm")
    provider.bind_tool_manager(
        MagicMock(
            get_schemas=MagicMock(
                return_value=[{"type": "function", "function": {"name": "demo"}}]
            )
        )
    )

    mock_response = SimpleNamespace(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="ok",
                    tool_calls=None,
                )
            )
        ],
    )

    provider.client = MagicMock()
    provider.client.chat.completions.create.return_value = mock_response

    provider.chat([Message(role="user", content="hi")])

    call_kwargs = provider.client.chat.completions.create.call_args.kwargs

    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


def test_vllm_provider_sends_tools_when_enabled(monkeypatch) -> None:

    _reset_provider_env(
        monkeypatch,
        MODEL_PROVIDER="vllm",
        VLLM_ENDPOINT="http://127.0.0.1:8000/v1",
        MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct",
        VLLM_ENABLE_TOOL_CALLING="true",
    )

    provider = create_llm_provider("vllm")
    provider.bind_tool_manager(
        MagicMock(
            get_schemas=MagicMock(
                return_value=[{"type": "function", "function": {"name": "demo"}}]
            )
        )
    )

    mock_response = SimpleNamespace(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="ok",
                    tool_calls=None,
                )
            )
        ],
    )

    provider.client = MagicMock()
    provider.client.chat.completions.create.return_value = mock_response

    provider.chat([Message(role="user", content="hi")])

    call_kwargs = provider.client.chat.completions.create.call_args.kwargs

    assert call_kwargs["tools"]
    assert call_kwargs["tool_choice"] == "auto"


def test_openai_compat_vllm_backend_omits_tools_by_default(monkeypatch) -> None:

    monkeypatch.setenv("VLLM_ENABLE_TOOL_CALLING", "false")
    reset_settings_cache()

    backend = OpenAICompatBackend(
        backend_kind=InferenceBackendKind.VLLM,
        api_key="EMPTY",
        base_url="http://127.0.0.1:8000/v1",
    )
    backend.bind_tool_manager(
        MagicMock(
            get_schemas=MagicMock(
                return_value=[{"type": "function", "function": {"name": "demo"}}]
            )
        )
    )

    mock_response = SimpleNamespace(
        model="Qwen/Qwen2.5-0.5B-Instruct",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="ok",
                    tool_calls=None,
                )
            )
        ],
        usage=None,
    )

    backend.client = MagicMock()
    backend.client.chat.completions.create.return_value = mock_response

    backend.chat([Message(role="user", content="hi")])

    call_kwargs = backend.client.chat.completions.create.call_args.kwargs

    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("openai", OpenAIProvider),
        ("local", LocalLLMProvider),
        ("vllm", VLLMProvider),
    ],
)
def test_provider_switch_via_factory(
    provider_name: str,
    expected_type: type[BaseLLM],
) -> None:

    provider = create_llm_provider(provider_name)

    assert isinstance(provider, expected_type)


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("openai", OpenAIProvider),
        ("local", LocalLLMProvider),
        ("vllm", VLLMProvider),
    ],
)
def test_chat_agent_auto_selects_provider(
    monkeypatch,
    provider_name: str,
    expected_type: type[BaseLLM],
) -> None:

    env = {
        "MODEL_PROVIDER": provider_name,
        "MODEL_NAME": "Qwen2.5",
    }

    if provider_name == "local":

        env["LOCAL_MODEL_ID"] = "Qwen/Qwen2.5-0.5B-Instruct"

    _reset_provider_env(monkeypatch, **env)

    agent = ChatAgent(
        config=AgentConfig(
            max_iterations=1,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        ),
    )

    assert isinstance(agent.client, expected_type)


def test_same_agent_interface_across_providers() -> None:

    for provider_name in ("openai", "local", "vllm"):

        provider = create_llm_provider(provider_name)

        assert hasattr(provider, "chat")
        assert hasattr(provider, "bind_tool_manager")
        assert callable(provider.chat)
