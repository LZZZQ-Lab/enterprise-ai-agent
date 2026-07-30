from __future__ import annotations

from typing import Any

from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.specialized.planner_agent import PlannerAgent
from app.agents.specialized.research_agent import ResearchAgent
from app.agents.specialized.reviewer_agent import ReviewerAgent
from app.agents.specialized.writer_agent import WriterAgent
from app.config import AgentConfig


def register_specialized_agents(
    registry: AgentRegistry,
    *,
    config: AgentConfig | None = None,
    client: Any | None = None,
) -> None:
    """
    向 Platform AgentRegistry 注册专职 Agent。
    """

    shared_kwargs: dict[str, Any] = {}

    if config is not None:

        shared_kwargs["config"] = config

    if client is not None:

        shared_kwargs["client"] = client

    registry.register(
        "planner",
        PlannerAgent,
    )

    registry.register(
        "research",
        ResearchAgent,
    )

    registry.register(
        "writer",
        WriterAgent,
    )

    registry.register(
        "reviewer",
        ReviewerAgent,
    )


def create_proposal_runtime(
    config: AgentConfig | None = None,
    client: Any | None = None,
) -> AgentRuntime:
    """
    创建已注册专职 Agent 的 Runtime（供 ManagerAgent 使用）。
    """

    from app.agents.registry import AgentRegistry

    registry = AgentRegistry()

    registry.register("planner", PlannerAgent)
    registry.register("research", ResearchAgent)
    registry.register("writer", WriterAgent)
    registry.register("reviewer", ReviewerAgent)

    return AgentRuntime(
        registry=registry,
        default_config=config,
    )
