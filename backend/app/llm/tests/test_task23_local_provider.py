"""
Task 2.3 Local LLM Provider 集成测试。

运行:
    cd backend
    python -m app.llm.tests.test_task23_local_provider
"""

from __future__ import annotations

import os

from app.config.settings import reset_settings_cache
from app.llm.factory import create_llm_provider
from app.llm.factory import reset_llm_client_cache
from app.llm.local_provider import LocalLLMProvider
from app.llm.types import Message


def test_local_llm_provider_chat_mock() -> None:

    class FakeInference:

        model_id = "Qwen/Qwen2.5-0.5B-Instruct"

        def generate(self, messages, **kwargs) -> str:

            return "你好，我是本地 Qwen 助手。"

    provider = LocalLLMProvider(inference=FakeInference())

    result = provider.chat(
        [Message(role="user", content="你好，请介绍一下自己")],
        use_tools=False,
    )

    assert result.model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert "Qwen" in (result.content or "")


def test_factory_local_from_env() -> None:

    os.environ["MODEL_PROVIDER"] = "local"
    os.environ["MODEL_NAME"] = "Qwen2.5"

    reset_settings_cache()
    reset_llm_client_cache()

    provider = create_llm_provider()

    assert isinstance(provider, LocalLLMProvider)
    assert provider.model_id == "Qwen/Qwen2.5-0.5B-Instruct"


def test_agent_uses_local_provider_without_code_change() -> None:

    os.environ["MODEL_PROVIDER"] = "local"
    os.environ["MODEL_NAME"] = "Qwen2.5"

    reset_settings_cache()
    reset_llm_client_cache()

    from app.agents.chat_agent import ChatAgent
    from app.config import AgentConfig

    agent = ChatAgent(
        config=AgentConfig(
            max_iterations=1,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        ),
    )

    assert isinstance(agent.client, LocalLLMProvider)


def run_all_tests() -> None:

    test_local_llm_provider_chat_mock()
    test_factory_local_from_env()
    test_agent_uses_local_provider_without_code_change()

    print("Task 2.3 Local LLM Provider tests passed.")


if __name__ == "__main__":

    run_all_tests()
