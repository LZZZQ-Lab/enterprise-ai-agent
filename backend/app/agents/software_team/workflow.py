"""
Phase 5.1：动态任务规划与工作流（非硬编码流水线）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.software_team.task import SoftwareProject
from app.agents.software_team.task import SoftwareTeamTask
from app.agents.software_team.task import TaskStatus
from app.config import AgentConfig


@dataclass(frozen=True)
class AgentCatalogEntry:
    """PM 可分配的 Agent 角色（非固定顺序）。"""

    agent: str
    role: str
    description: str


DEFAULT_AGENT_CATALOG: tuple[AgentCatalogEntry, ...] = (
    AgentCatalogEntry(
        agent="product",
        role="Product Agent",
        description="需求分析、用户故事、PRD 与验收标准",
    ),
    AgentCatalogEntry(
        agent="architecture",
        role="Architecture Agent",
        description="系统设计、模块划分、技术选型与 Architecture 文档",
    ),
    AgentCatalogEntry(
        agent="developer",
        role="Developer Agent",
        description="后端/前端/全栈代码实现",
    ),
    AgentCatalogEntry(
        agent="reviewer",
        role="Reviewer Agent",
        description="代码与文档审查、风险与改进建议",
    ),
    AgentCatalogEntry(
        agent="tester",
        role="Tester Agent",
        description="测试用例、自动化测试与质量报告",
    ),
    AgentCatalogEntry(
        agent="devops",
        role="DevOps Agent",
        description="构建、部署、CI/CD 与运行手册",
    ),
)


class TaskPlanningClient(Protocol):
    def chat(self, messages, use_tools: bool = True): ...


def _catalog_for_prompt(
    catalog: tuple[AgentCatalogEntry, ...],
) -> str:

    lines = []

    for entry in catalog:

        lines.append(
            f"- agent={entry.agent!r}: {entry.role} — {entry.description}"
        )

    return "\n".join(lines)


def _extract_json_array(text: str) -> list[dict[str, Any]]:

    stripped = text.strip()

    fence = re.search(
        r"```(?:json)?\s*(\[[\s\S]*?\])\s*```",
        stripped,
    )

    if fence:

        stripped = fence.group(1)

    else:

        start = stripped.find("[")
        end = stripped.rfind("]")

        if start >= 0 and end > start:

            stripped = stripped[start : end + 1]

    data = json.loads(stripped)

    if not isinstance(data, list):

        raise ValueError("Task plan must be a JSON array")

    return data


class SoftwareTeamWorkflow:
    """
    理解目标 → 规划 Task List →（可选）Runtime 执行。
    """

    PLANNING_MARKER = "SOFTWARE_TEAM_TASK_PLAN"

    def __init__(
        self,
        *,
        client: TaskPlanningClient | None = None,
        catalog: tuple[AgentCatalogEntry, ...] = DEFAULT_AGENT_CATALOG,
        config: AgentConfig | None = None,
    ) -> None:

        self._client = client
        self._catalog = catalog
        self._config = config or AgentConfig.from_env()

    def understand_goal(
        self,
        requirement: str,
    ) -> str:

        if self._client is None:

            return self._fallback_goal(requirement)

        from app.llm.types import Message

        prompt = (
            f"{self.PLANNING_MARKER}_GOAL\n"
            "用一两句话概括下列软件需求的业务目标与技术边界，"
            "不要列出任务清单：\n\n"
            f"{requirement}"
        )

        result = self._client.chat(
            [Message(role="user", content=prompt)],
            use_tools=False,
        )

        text = (result.content or "").strip()

        return text or self._fallback_goal(requirement)

    def plan_tasks(
        self,
        requirement: str,
        goal_summary: str,
    ) -> list[SoftwareTeamTask]:

        if self._client is None:

            return self._fallback_tasks(requirement)

        from app.llm.types import Message

        allowed = {entry.agent for entry in self._catalog}

        prompt = (
            f"{self.PLANNING_MARKER}\n"
            "你是 AI 软件团队的 Project Manager。根据用户需求生成任务列表。\n\n"
            f"【目标摘要】\n{goal_summary}\n\n"
            f"【用户需求】\n{requirement}\n\n"
            "【可分配 Agent】\n"
            f"{_catalog_for_prompt(self._catalog)}\n\n"
            "要求：\n"
            "1. 仅输出 JSON 数组，不要 markdown 说明\n"
            "2. 每项字段：title, description, agent\n"
            f"3. agent 只能从 {sorted(allowed)} 中选择\n"
            "4. 任务应覆盖从需求到部署的合理顺序，但由你决定粒度与数量\n"
            "5. 需贴合当前需求，不要套用无关模板\n\n"
            "示例格式：\n"
            '[{"title":"...","description":"...","agent":"product"}]'
        )

        result = self._client.chat(
            [Message(role="user", content=prompt)],
            use_tools=False,
        )

        raw = result.content or ""

        try:

            items = _extract_json_array(raw)

        except (json.JSONDecodeError, ValueError):

            return self._fallback_tasks(requirement)

        tasks: list[SoftwareTeamTask] = []

        for item in items:

            agent = str(item.get("agent", "")).strip()

            if agent not in allowed:

                continue

            title = str(item.get("title", "")).strip()

            if not title:

                continue

            tasks.append(
                SoftwareTeamTask(
                    title=title,
                    description=str(
                        item.get("description", "")
                    ).strip()
                    or title,
                    agent=agent,
                )
            )

        if tasks:

            return tasks

        return self._fallback_tasks(requirement)

    def create_project(
        self,
        requirement: str,
    ) -> SoftwareProject:

        goal = self.understand_goal(requirement)
        tasks = self.plan_tasks(requirement, goal)
        name = self._project_name(requirement)

        return SoftwareProject(
            requirement=requirement,
            goal_summary=goal,
            name=name,
            tasks=tasks,
        )

    def execute_tasks(
        self,
        project: SoftwareProject,
        runtime: AgentRuntime,
        *,
        session_id: str,
    ) -> SoftwareProject:

        shared: dict[str, Any] = {
            "project_id": project.id,
            "project_name": project.name,
            "goal_summary": project.goal_summary,
        }

        for task in project.tasks:

            task.status = TaskStatus.RUNNING

            brief = (
                f"【项目】{project.name}\n"
                f"【目标】{project.goal_summary}\n"
                f"【任务】{task.title}\n"
                f"【说明】{task.description}\n"
                f"【原始需求】{project.requirement}"
            )

            result = runtime.run(
                AgentTask(
                    session_id=session_id,
                    user_message=brief,
                    agent_name=task.agent,
                    shared_context=dict(shared),
                    metadata={
                        "software_team_task_id": task.id,
                        "project_id": project.id,
                    },
                ),
                config=self._config,
            )

            task.result = result.content or ""
            task.status = (
                TaskStatus.COMPLETED
                if result.success
                else TaskStatus.FAILED
            )

            shared[f"task:{task.id}"] = task.result

        return project

    @staticmethod
    def _project_name(requirement: str) -> str:

        text = requirement.strip().replace("\n", " ")

        if len(text) <= 48:

            return text

        return text[:45] + "..."

    @staticmethod
    def _fallback_goal(requirement: str) -> str:

        return (
            f"交付满足以下描述的可运行软件：{requirement.strip()[:200]}"
        )

    def _fallback_tasks(
        self,
        requirement: str,
    ) -> list[SoftwareTeamTask]:

        _ = requirement

        return [
            SoftwareTeamTask(
                title="需求与范围分析",
                description="梳理用户故事、功能范围与验收标准，输出 PRD",
                agent="product",
            ),
            SoftwareTeamTask(
                title="系统架构设计",
                description="定义模块、接口、数据模型与技术栈，输出 Architecture",
                agent="architecture",
            ),
            SoftwareTeamTask(
                title="功能开发与集成",
                description="按架构实现核心业务与 API/UI",
                agent="developer",
            ),
            SoftwareTeamTask(
                title="代码审查",
                description="审查实现质量、安全与可维护性",
                agent="reviewer",
            ),
            SoftwareTeamTask(
                title="测试与质量验证",
                description="编写并执行测试，修复缺陷",
                agent="tester",
            ),
            SoftwareTeamTask(
                title="部署与交付",
                description="构建镜像/Compose，编写部署与运维说明",
                agent="devops",
            ),
        ]
