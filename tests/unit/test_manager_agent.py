"""ManagerAgent 多 Agent 项目方案协作测试。"""

from __future__ import annotations

import pytest

from app.agents.manager_agent import ManagerAgent
from app.agents.runtime import AgentRuntime
from app.agents.specialized.factory import create_proposal_runtime
from app.agents.specialized.planner_agent import PlannerAgent
from app.agents.specialized.research_agent import ResearchAgent
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.llm.types import ChatResult


class PipelineMockLLM:
    """按 Prompt 关键词返回各角色 Mock 输出。"""

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(
        self,
        messages,
        use_tools=True,
    ) -> ChatResult:

        user = messages[-1].content or ""

        if user.startswith("请审阅") or "【REVIEWER】" in user:

            content = "FINAL: 审定版项目方案"

        elif user.startswith("请撰写") or "【WRITER】" in user:

            content = "DRAFT: 项目方案初稿正文"

        elif user.startswith("请针对") or "【RESEARCH】" in user:

            content = "RESEARCH: 行业背景与合规约束"

        elif user.startswith("请为以下") or "【PLANNER】" in user:

            content = "PLAN: 三阶段里程碑与风险清单"

        else:

            content = "OK"

        return ChatResult(
            model="pipeline-mock",
            content=content,
        )


@pytest.fixture
def proposal_config() -> AgentConfig:

    return AgentConfig(
        max_iterations=2,
        enable_mcp=False,
        enable_rag=False,
        enable_knowledge_tool=False,
        enable_trace=False,
        enable_planner=False,
    )


def test_specialized_agents_registered_on_proposal_runtime(
    proposal_config: AgentConfig,
) -> None:

    runtime = create_proposal_runtime(
        config=proposal_config,
        client=PipelineMockLLM(),
    )

    for name in (
        "planner",
        "research",
        "writer",
        "reviewer",
    ):

        assert runtime.registry.has(name)


def test_manager_generates_project_proposal(
    proposal_config: AgentConfig,
) -> None:

    manager = ManagerAgent(
        config=proposal_config,
        client=PipelineMockLLM(),
    )

    result = manager.run(
        AgentContext(
            session_id="ma-test",
            user_message="请生成企业 AI 平台建设项目方案",
        )
    )

    assert result.success is True
    assert "FINAL:" in result.content
    assert "PLAN:" in result.content
    assert "RESEARCH:" in result.content
    assert "DRAFT:" in result.content
    assert "项目方案交付" in result.content


def test_runtime_can_run_planner_directly(
    proposal_config: AgentConfig,
) -> None:

    from app.agents.runtime import AgentTask

    runtime = AgentRuntime(
        registry=__import__(
            "app.agents.registry",
            fromlist=["AgentRegistry"],
        ).AgentRegistry(),
        default_config=proposal_config,
    )

    runtime.registry.register("planner", PlannerAgent)

    result = runtime.run(
        AgentTask(
            session_id="planner-only",
            user_message="请为以下用户任务制定项目方案大纲：测试任务",
            agent_name="planner",
        ),
        client=PipelineMockLLM(),
    )

    assert result.success
    assert "PLAN:" in (result.content or "")
