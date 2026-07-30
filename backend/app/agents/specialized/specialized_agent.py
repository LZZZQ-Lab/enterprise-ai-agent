from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.chat_agent import ChatAgent
from app.agents.specialized.profiles import SPECIALIZED_PROFILES
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.multi_agent.profile import AgentProfile
from app.multi_agent.role_agent import create_role_agent


def create_specialized_chat_agent(
    profile: AgentProfile,
    config: AgentConfig | None = None,
    client: Any | None = None,
) -> ChatAgent:
    """
    基于 Profile 创建 ChatAgent（复用 RoleAgent 工厂，不复制 ChatAgent 代码）。
    """

    role_agent = create_role_agent(
        profile,
        base_config=config,
        client=client,
    )

    return role_agent.chat_agent


class SpecializedAgent(BaseAgent):
    """
    专职 Agent 基类：委托 ChatAgent 执行，统一 Runtime 接口。
    """

    role_name: str = ""

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: Any | None = None,
        chat_agent: ChatAgent | None = None,
    ) -> None:

        super().__init__()

        if not self.role_name:

            raise ValueError(
                "SpecializedAgent subclass must set role_name"
            )

        self._profile = SPECIALIZED_PROFILES[self.role_name]

        self._chat_agent = (
            chat_agent
            or create_specialized_chat_agent(
                self._profile,
                config=config,
                client=client,
            )
        )

    @property
    def name(self) -> str:

        return self.role_name

    @property
    def profile(self) -> AgentProfile:

        return self._profile

    @property
    def chat_agent(self) -> ChatAgent:

        return self._chat_agent

    def get_capabilities(self) -> list[str]:

        return list(self._profile.capabilities)

    def can_handle(
        self,
        task_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:

        lower_input = task_input.lower()

        for keyword in self._profile.keywords:

            if keyword.lower() in lower_input:

                return True

        task_type = (metadata or {}).get("task_type", "")

        return task_type in self._profile.capabilities

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        context.agent_name = self.name
        context.agent_role = self._profile.role

        context.metadata.setdefault(
            "current_task",
            context.user_message,
        )

        merged_shared = {
            **context.shared_context,
        }

        if merged_shared:

            context.metadata["shared_context"] = merged_shared

        return self._chat_agent.execute(context)


class PlannerAgent(SpecializedAgent):

    role_name = "planner"


class ResearchAgent(SpecializedAgent):

    role_name = "research"


class WriterAgent(SpecializedAgent):

    role_name = "writer"


class ReviewerAgent(SpecializedAgent):

    role_name = "reviewer"
