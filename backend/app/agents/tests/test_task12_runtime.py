"""
Task 1.2 Agent Runtime 架构测试。

运行:
    cd backend
    python -m app.agents.tests.test_task12_runtime
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class _EchoAgent(BaseAgent):
    """测试用最小 Agent。"""

    def __init__(
        self,
        prefix: str = "echo",
        **kwargs: Any,
    ) -> None:

        super().__init__()
        self._prefix = prefix

    @property
    def name(self) -> str:

        return "echo"

    def get_capabilities(self) -> list[str]:

        return ["echo", "test"]

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        return AgentResult(
            success=True,
            model="mock",
            content=f"{self._prefix}:{context.user_message}",
        )


def test_base_agent_interface() -> None:

    agent = _EchoAgent()

    assert agent.name == "echo"
    assert agent.can_handle("anything") is True
    assert "echo" in agent.get_capabilities()


def test_registry() -> None:

    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)

    assert reg.has("echo")
    assert reg.get("echo") is _EchoAgent
    assert "echo" in reg.list_agents()


def test_factory_create() -> None:

    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)

    from app.agents.factory import AgentFactory

    agent = AgentFactory.create("echo", registry=reg, prefix="test")

    assert isinstance(agent, _EchoAgent)
    assert agent._prefix == "test"


def test_runtime_create_context() -> None:

    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)
    runtime = AgentRuntime(registry=reg, default_agent="echo")

    task = AgentTask(
        session_id="s1",
        user_message="hello",
        agent_name="echo",
        metadata={"source": "test"},
    )

    context = runtime.create_context(task)

    assert context.session_id == "s1"
    assert context.user_message == "hello"
    assert context.agent_name == "echo"
    assert context.metadata["source"] == "test"


def test_runtime_run() -> None:

    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)
    runtime = AgentRuntime(registry=reg, default_agent="echo")

    result = runtime.run(
        AgentTask(
            session_id="s2",
            user_message="world",
            agent_name="echo",
        ),
        config=AgentConfig(max_iterations=1),
    )

    assert result.success is True
    assert result.content == "echo:world"


def test_runtime_default_agent() -> None:

    reg = AgentRegistry()
    reg.register("echo", _EchoAgent)
    runtime = AgentRuntime(registry=reg, default_agent="echo")

    result = runtime.run(
        AgentTask(
            session_id="s3",
            user_message="default",
        ),
    )

    assert result.content == "echo:default"


def test_chat_agent_via_runtime() -> None:

    from app.agents.registry import registry as global_registry

    assert global_registry.has("chat")

    runtime = AgentRuntime(default_agent="chat")

    assert runtime.resolve_agent_name() == "chat"
    assert runtime.registry.get("chat") is not None


def run_all_tests() -> None:

    test_base_agent_interface()
    test_registry()
    test_factory_create()
    test_runtime_create_context()
    test_runtime_run()
    test_runtime_default_agent()
    test_chat_agent_via_runtime()

    print("Task 1.2 Agent Runtime tests passed.")


if __name__ == "__main__":

    run_all_tests()
