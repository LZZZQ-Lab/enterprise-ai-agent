from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.registry import registry as registry_module
from app.config import AgentConfig


class AgentFactory:
    """
    Agent 实例工厂。

    通过 Registry 查找 Agent 类型并创建实例。
    """

    @staticmethod
    def create(
        name: str,
        config: AgentConfig | None = None,
        registry: AgentRegistry | None = None,
        **kwargs: Any,
    ) -> BaseAgent:

        agent_registry = registry or registry_module

        agent_cls = agent_registry.get(name)

        if config is not None:

            kwargs.setdefault("config", config)

        return agent_cls(**kwargs)

    @staticmethod
    def get(
        name: str,
        config: AgentConfig | None = None,
        registry: AgentRegistry | None = None,
        **kwargs: Any,
    ) -> BaseAgent:
        """
        向后兼容别名。
        """

        return AgentFactory.create(
            name,
            config=config,
            registry=registry,
            **kwargs,
        )
