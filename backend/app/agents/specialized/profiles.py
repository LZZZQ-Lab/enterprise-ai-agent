from __future__ import annotations

from app.multi_agent.profile import AgentProfile

PLANNER_PROFILE = AgentProfile(
    name="planner",
    role="Project Planner",
    description=(
        "分解用户任务，输出清晰的项目方案大纲：目标、阶段、"
        "里程碑、风险与资源假设。使用条目与标题结构。"
    ),
    capabilities=["planning", "plan", "方案", "规划"],
    keywords=["规划", "计划", "plan", "里程碑", "方案大纲"],
)

RESEARCH_PROFILE = AgentProfile(
    name="research",
    role="Research Analyst",
    description=(
        "根据规划收集要点、行业背景、约束与参考信息。"
        "可结合企业知识库事实；缺少信息时明确标注假设。"
    ),
    capabilities=["research", "调研", "分析"],
    keywords=["调研", "研究", "research", "背景", "分析"],
    supported_tools=["search_knowledge"],
)

WRITER_PROFILE = AgentProfile(
    name="writer",
    role="Proposal Writer",
    description=(
        "基于规划与调研材料撰写完整项目方案文档，"
        "包含概述、范围、实施步骤、交付物与时间线。"
    ),
    capabilities=["writing", "writer", "撰写"],
    keywords=["撰写", "写作", "writer", "文档", "方案"],
)

REVIEWER_PROFILE = AgentProfile(
    name="reviewer",
    role="Quality Reviewer",
    description=(
        "审阅方案草稿，检查完整性、一致性与可执行性，"
        "输出修订后的最终版或明确的改进清单。"
    ),
    capabilities=["review", "审阅", "quality"],
    keywords=["审阅", "review", "评审", "质量"],
)

SPECIALIZED_PROFILES: dict[str, AgentProfile] = {
    profile.name: profile
    for profile in (
        PLANNER_PROFILE,
        RESEARCH_PROFILE,
        WRITER_PROFILE,
        REVIEWER_PROFILE,
    )
}
