from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.specialized.factory import create_proposal_runtime
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class ManagerAgent(BaseAgent):
    """
    多 Agent 协作管理器。

    流程：User Task → Planner → Executor(Research + Writer) → Reviewer
    通过 AgentRuntime 调度专职 Agent，不复制 ChatAgent 实现。
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        runtime: AgentRuntime | None = None,
        client: Any | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()

        self._runtime = runtime or create_proposal_runtime(
            config=self._config,
            client=client,
        )

        self._client = client

    @property
    def name(self) -> str:

        return "manager"

    @property
    def runtime(self) -> AgentRuntime:

        return self._runtime

    def get_capabilities(self) -> list[str]:

        return [
            "multi_agent",
            "project_proposal",
            "orchestration",
        ]

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        session_id = context.session_id
        user_task = context.user_message

        shared: dict[str, Any] = dict(context.shared_context)

        shared["root_task"] = user_task

        plan_result = self._run_role(
            session_id=session_id,
            agent_name="planner",
            user_message=self._planner_prompt(user_task),
            shared=shared,
            history=context.history,
        )

        if not plan_result.success:

            return plan_result

        shared["plan"] = plan_result.content or ""

        research_result = self._run_role(
            session_id=session_id,
            agent_name="research",
            user_message=self._research_prompt(
                user_task,
                shared["plan"],
            ),
            shared=shared,
            history=context.history,
        )

        if not research_result.success:

            return research_result

        shared["research"] = research_result.content or ""

        writer_result = self._run_role(
            session_id=session_id,
            agent_name="writer",
            user_message=self._writer_prompt(
                user_task,
                shared["plan"],
                shared["research"],
            ),
            shared=shared,
            history=context.history,
        )

        if not writer_result.success:

            return writer_result

        shared["draft"] = writer_result.content or ""

        review_result = self._run_role(
            session_id=session_id,
            agent_name="reviewer",
            user_message=self._reviewer_prompt(
                user_task,
                shared["draft"],
            ),
            shared=shared,
            history=context.history,
        )

        if not review_result.success:

            return review_result

        final_content = self._format_deliverable(
            user_task=user_task,
            plan=shared["plan"],
            research=shared["research"],
            draft=shared["draft"],
            reviewed=review_result.content or "",
        )

        return AgentResult(
            success=True,
            model="manager",
            content=final_content,
        )

    def _run_role(
        self,
        *,
        session_id: str,
        agent_name: str,
        user_message: str,
        shared: dict[str, Any],
        history,
    ) -> AgentResult:

        return self._runtime.run(
            AgentTask(
                session_id=session_id,
                user_message=user_message,
                agent_name=agent_name,
                history=list(history),
                shared_context=dict(shared),
                metadata={
                    "pipeline_stage": agent_name,
                    "root_task": shared.get("root_task", ""),
                },
            ),
            config=self._config,
            client=self._client,
        )

    @staticmethod
    def _planner_prompt(user_task: str) -> str:

        return (
            "请为以下用户任务制定项目方案大纲（目标、阶段、"
            "里程碑、风险、资源假设）：\n\n"
            f"{user_task}"
        )

    @staticmethod
    def _research_prompt(
        user_task: str,
        plan: str,
    ) -> str:

        return (
            "请针对下列任务与规划大纲，补充调研要点、"
            "背景约束与关键参考（如需企业事实可说明假设）：\n\n"
            f"【用户任务】\n{user_task}\n\n"
            f"【规划大纲】\n{plan}"
        )

    @staticmethod
    def _writer_prompt(
        user_task: str,
        plan: str,
        research: str,
    ) -> str:

        return (
            "请撰写完整《项目方案》初稿，结构清晰，"
            "包含概述、范围、实施步骤、交付物与时间线：\n\n"
            f"【用户任务】\n{user_task}\n\n"
            f"【规划】\n{plan}\n\n"
            f"【调研】\n{research}"
        )

    @staticmethod
    def _reviewer_prompt(
        user_task: str,
        draft: str,
    ) -> str:

        return (
            "请审阅下列项目方案草稿，输出修订后的最终版"
            "（保留 Markdown 标题结构，修正遗漏与矛盾）：\n\n"
            f"【用户任务】\n{user_task}\n\n"
            f"【草稿】\n{draft}"
        )

    @staticmethod
    def _format_deliverable(
        *,
        user_task: str,
        plan: str,
        research: str,
        draft: str,
        reviewed: str,
    ) -> str:

        return (
            f"# 项目方案交付\n\n"
            f"## 用户任务\n{user_task}\n\n"
            f"## 最终方案\n{reviewed}\n\n"
            f"---\n\n"
            f"## 附录：规划大纲\n{plan}\n\n"
            f"## 附录：调研摘要\n{research}\n\n"
            f"## 附录：写作初稿\n{draft}\n"
        )
