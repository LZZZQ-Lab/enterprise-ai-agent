"""Agent 创建测试。"""

from __future__ import annotations

from app.agents.chat_agent import ChatAgent
from app.agents.factory import AgentFactory
from app.agents.registry import registry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.config import AgentConfig

from tests.fixtures.mock_llm import MockLLM


def test_agent_registry_has_chat() -> None:

    assert registry.has("chat")
    assert "chat" in registry.list_agents()


def test_agent_factory_creates_chat_agent(
    agent_config: AgentConfig,
) -> None:

    agent = AgentFactory.create(
        "chat",
        config=agent_config,
        client=MockLLM(),
    )

    assert isinstance(agent, ChatAgent)
    assert agent.name == "chat"
    assert agent.prompt_builder is not None
    assert agent.agent_executor is not None


def test_chat_agent_capabilities(
    agent_config: AgentConfig,
) -> None:

    agent = ChatAgent(
        config=agent_config,
        client=MockLLM(),
    )

    capabilities = agent.get_capabilities()

    assert "chat" in capabilities
    assert "tool_calling" in capabilities
    assert agent.can_handle("hello") is True


def test_agent_runtime_resolves_default_agent() -> None:

    runtime = AgentRuntime(default_agent="chat")

    assert runtime.resolve_agent_name() == "chat"
    assert runtime.registry.has("chat")


def test_agent_runtime_run_with_mock_agent(
    agent_config: AgentConfig,
) -> None:

    from app.agents.base import BaseAgent
    from app.agents.registry import AgentRegistry
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult

    class EchoAgent(BaseAgent):

        def __init__(self, **kwargs: object) -> None:

            super().__init__()

        def execute(
            self,
            context: AgentContext,
        ) -> AgentResult:

            return AgentResult(
                success=True,
                model="mock",
                content=f"echo:{context.user_message}",
            )

    reg = AgentRegistry()
    reg.register("echo", EchoAgent)
    runtime = AgentRuntime(registry=reg, default_agent="echo")

    result = runtime.run(
        AgentTask(
            session_id="test-session",
            user_message="ping",
            agent_name="echo",
        ),
        config=agent_config,
    )

    assert result.success is True
    assert result.content == "echo:ping"
