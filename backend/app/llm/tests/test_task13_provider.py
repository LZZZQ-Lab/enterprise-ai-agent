"""
Task 1.3 LLM Provider 抽象层测试。

运行:
    cd backend
    python -m app.llm.tests.test_task13_provider
"""

from __future__ import annotations

import pytest

from app.llm.base import BaseLLM
from app.llm.factory import create_llm_provider
from app.llm.local_provider import LocalLLMProvider
from app.llm.local_provider import LocalProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.types import Message
from app.llm.vllm_provider import VLLMProvider


def test_base_llm_is_abstract() -> None:

    with pytest.raises(TypeError):

        BaseLLM()


def test_factory_default_openai() -> None:

    provider = create_llm_provider("openai")

    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, BaseLLM)
    assert hasattr(provider, "chat")
    assert hasattr(provider, "bind_tool_manager")


def test_factory_local_provider() -> None:

    provider = create_llm_provider("local")

    assert isinstance(provider, LocalLLMProvider)
    assert provider.model_id


def test_local_provider_mock_chat() -> None:

    class FakeInference:

        model_id = "fake/Qwen2.5-0.5B-Instruct"

        def generate(self, messages, **kwargs) -> str:

            return "mock answer"

    provider = LocalLLMProvider(inference=FakeInference())

    result = provider.chat(
        [Message(role="user", content="hello")],
        use_tools=False,
    )

    assert result.content == "mock answer"


def test_factory_vllm_provider() -> None:

    provider = create_llm_provider("vllm")

    assert isinstance(provider, VLLMProvider)
    assert isinstance(provider, BaseLLM)


def test_get_llm_client_backward_compat() -> None:

    from app.llm.client import LLMClient
    from app.llm.factory import get_llm_client

    client = get_llm_client()

    assert isinstance(client, BaseLLM)
    assert LLMClient is OpenAIProvider


def test_openai_tool_argument_recovery() -> None:

    broken = '{"path": "D:\\\\tmp\\\\a.txt", "content": "hello'

    args = OpenAIProvider._parse_arguments("write_file", broken)

    assert args["path"] == "D:\\tmp\\a.txt"
    assert args["content"] == "hello"


def run_all_tests() -> None:

    test_base_llm_is_abstract()
    test_factory_default_openai()
    test_factory_local_provider()
    test_local_provider_mock_chat()
    test_factory_vllm_provider()
    test_get_llm_client_backward_compat()
    test_openai_tool_argument_recovery()

    print("Task 1.3 LLM Provider tests passed.")


if __name__ == "__main__":

    run_all_tests()
