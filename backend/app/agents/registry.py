from __future__ import annotations

from typing import Type

from app.agents.base import BaseAgent


class AgentRegistry:
    """
    Agent 注册中心。

    负责 Agent 类型注册与查找，供 Factory / Runtime 使用。
    """

    DEFAULT_AGENT = "chat"

    def __init__(self) -> None:

        self._agents: dict[str, Type[BaseAgent]] = {}

    def register(
        self,
        name: str,
        agent_cls: Type[BaseAgent],
    ) -> None:

        self._agents[name] = agent_cls

    def unregister(
        self,
        name: str,
    ) -> None:

        self._agents.pop(name, None)

    def get(
        self,
        name: str,
    ) -> Type[BaseAgent]:

        if name not in self._agents:

            raise ValueError(
                f"Agent '{name}' not found. "
                f"Registered: {self.list_agents()}"
            )

        return self._agents[name]

    def has(
        self,
        name: str,
    ) -> bool:

        return name in self._agents

    def list_agents(self) -> list[str]:

        return list(self._agents.keys())

    def get_default(self) -> str:

        if self.has(self.DEFAULT_AGENT):

            return self.DEFAULT_AGENT

        agents = self.list_agents()

        if not agents:

            raise ValueError("No agents registered.")

        return agents[0]


registry = AgentRegistry()
