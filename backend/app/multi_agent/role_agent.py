from typing import Any

from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.multi_agent.agent import Agent
from app.multi_agent.profile import AgentProfile
from app.config import AgentConfig


class RoleAgent(Agent):
    """
    基于 Profile 的角色 Agent。

    包装 ChatAgent，注入独立 System Prompt 与能力标签，
    所有 Agent 使用统一 Runtime。
    """

    def __init__(
        self,
        profile: AgentProfile,
        chat_agent,
    ):

        self._profile = profile
        self._chat_agent = chat_agent

    @property
    def name(self) -> str:

        return self._profile.name

    @property
    def profile(self) -> AgentProfile:

        return self._profile

    @property
    def chat_agent(self):

        return self._chat_agent

    def run(
        self,
        context: AgentContext,
    ) -> AgentResult:

        context.agent_name = self._profile.name
        context.agent_role = self._profile.role

        if not context.metadata.get("current_task"):

            context.metadata["current_task"] = context.user_message

        return self._chat_agent.run(context)

    def can_handle(
        self,
        task_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:

        lower_input = task_input.lower()

        for keyword in self._profile.keywords:

            if keyword.lower() in lower_input:

                return True

        for capability in self._profile.capabilities:

            if capability.lower() in lower_input:

                return True

        task_type = (metadata or {}).get("task_type", "")

        if task_type in self._profile.capabilities:

            return True

        return False

    def get_capabilities(self) -> list[str]:

        return list(self._profile.capabilities)


def create_role_agent(
    profile: AgentProfile,
    base_config: AgentConfig | None = None,
    client: Any | None = None,
) -> RoleAgent:
    """
    工厂方法：创建带独立 System Prompt 的 RoleAgent。
    """

    from app.agents.chat_agent import ChatAgent

    config = base_config or AgentConfig.from_env()

    role_config = AgentConfig(
        max_iterations=config.max_iterations,
        temperature=config.temperature,
        tool_choice=config.tool_choice,
        system_prompt=(
            f"You are {profile.name}, a {profile.role}.\n\n"
            f"{profile.description}\n\n"
            "Reply in the same language as the user. "
            "Be concise and helpful."
        ),
        enable_rag=config.enable_rag,
        enable_knowledge_tool=config.enable_knowledge_tool,
        top_k=config.top_k,
        score_threshold=config.score_threshold,
        enable_mcp=config.enable_mcp,
        mcp_servers=list(config.mcp_servers),
        auto_discover_tools=config.auto_discover_tools,
        auto_discover_resources=config.auto_discover_resources,
        enable_planner=config.enable_planner,
        max_plan_steps=config.max_plan_steps,
        enable_trace=config.enable_trace,
        enable_metrics=config.enable_metrics,
        enable_evaluation=config.enable_evaluation,
        exporter_type=config.exporter_type,
        enable_multi_agent=config.enable_multi_agent,
        router_type=config.router_type,
        max_agents=config.max_agents,
        communication_mode=config.communication_mode,
    )

    chat_agent = ChatAgent(
        config=role_config,
        client=client,
    )

    return RoleAgent(
        profile=profile,
        chat_agent=chat_agent,
    )
