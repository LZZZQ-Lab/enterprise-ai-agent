from app.multi_agent.coordinator import Coordinator
from app.multi_agent.profile import AgentProfile
from app.multi_agent.registry import AgentRegistry
from app.multi_agent.role_agent import create_role_agent
from app.multi_agent.router import create_router
from app.multi_agent.template_agent import TemplateAgent
from app.config import AgentConfig
from app.agents.executor.tracer import AgentTracer


def create_travel_profiles() -> list[AgentProfile]:
    """
    东京旅行场景 Agent Profile 定义。
    """

    return [
        AgentProfile(
            name="travel",
            role="Travel Planner",
            description="负责整体旅行规划与景点推荐。",
            capabilities=["travel", "planning"],
            keywords=["旅行", "旅游", "travel", "东京", "景点"],
        ),
        AgentProfile(
            name="weather",
            role="Weather Advisor",
            description="负责查询目的地天气并提供出行建议。",
            capabilities=["weather"],
            keywords=["天气", "weather", "气温", "降雨"],
        ),
        AgentProfile(
            name="hotel",
            role="Hotel Advisor",
            description="负责酒店推荐与住宿建议。",
            capabilities=["hotel"],
            keywords=["酒店", "hotel", "住宿", "预订"],
        ),
        AgentProfile(
            name="summary",
            role="Summary Agent",
            description="负责汇总各 Agent 结果，生成最终建议。",
            capabilities=["summary"],
            keywords=["汇总", "总结", "summary"],
        ),
    ]


def create_travel_registry(
    config: AgentConfig | None = None,
    use_llm: bool = False,
) -> AgentRegistry:
    """
    注册 Travel / Weather / Hotel / Summary Agent。
    """

    config = config or AgentConfig.from_env(
        enable_multi_agent=True,
    )

    registry = AgentRegistry()

    if use_llm:

        for profile in create_travel_profiles():

            registry.register(
                create_role_agent(profile, config),
                profile,
            )

        return registry

    templates = {
        "travel": (
            "【景点推荐】\n"
            "基于任务「{task}」，推荐东京行程：\n"
            "- Day1: 浅草寺、晴空塔\n"
            "- Day2: 上野公园、秋叶原\n"
            "- Day3: 明治神宫、涩谷、新宿"
        ),
        "weather": (
            "【天气概况】\n"
            "东京未来一周：气温 18-26°C，偶有小雨。\n"
            "建议携带轻便外套与折叠伞。"
        ),
        "hotel": (
            "【酒店推荐】\n"
            "- 经济型：浅草/上野区域商务酒店\n"
            "- 中档：银座/东京站周边\n"
            "- 高端：六本木/丸之内 luxury 酒店"
        ),
        "summary": (
            "【东京旅行综合建议】\n\n"
            "根据各 Agent 结果，为您整理如下：\n\n"
            "{input}"
        ),
    }

    for profile in create_travel_profiles():

        registry.register(
            TemplateAgent(
                profile=profile,
                template=templates[profile.name],
            ),
            profile,
        )

    return registry


def create_travel_coordinator(
    config: AgentConfig | None = None,
    use_llm: bool = False,
    tracer: AgentTracer | None = None,
) -> Coordinator:
    """
    创建东京旅行 Multi-Agent Coordinator。
    """

    config = config or AgentConfig.from_env(
        enable_multi_agent=True,
        router_type="rule",
        max_agents=10,
        communication_mode="bus",
    )

    registry = create_travel_registry(
        config=config,
        use_llm=use_llm,
    )

    return Coordinator(
        registry=registry,
        config=config,
        router=create_router(config.router_type),
        tracer=tracer,
    )
