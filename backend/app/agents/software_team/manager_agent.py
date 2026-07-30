"""
Phase 5.1：Project Manager Agent — AI 软件团队总协调。
"""

from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.agents.runtime import AgentRuntime
from app.agents.software_team.task import SoftwareProject
from app.agents.software_team.workflow import SoftwareTeamWorkflow
from app.agents.software_team.workflow import TaskPlanningClient
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class ProjectManagerAgent(BaseAgent):
    """
    接收用户需求 → 理解目标 → 创建 Project → 拆分 Task → 分配 Agent。

    规划由 SoftwareTeamWorkflow + LLM 动态生成，非硬编码流水线。
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: TaskPlanningClient | None = None,
        runtime: AgentRuntime | None = None,
        workflow: SoftwareTeamWorkflow | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client
        self._runtime = runtime

        self._workflow = workflow or SoftwareTeamWorkflow(
            client=client,
            config=self._config,
        )

        self.last_project: SoftwareProject | None = None

    @property
    def name(self) -> str:

        return "project_manager"

    def get_capabilities(self) -> list[str]:

        return [
            "software_team",
            "task_planning",
            "orchestration",
        ]

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        requirement = context.user_message.strip()

        if not requirement:

            return AgentResult(
                success=False,
                model="project_manager",
                content="Empty requirement.",
            )

        project = self._workflow.create_project(requirement)

        from app.memory.memory_manager import get_default_enterprise_memory_manager

        memory = get_default_enterprise_memory_manager()
        project_id = context.metadata.get("project_id") or context.session_id
        memory.record_software_project(
            project_id,
            agent_name=self.name,
            requirement=requirement,
            task_list_text=self.format_task_list(project),
            tasks_json=json.dumps(
                [
                    {
                        "id": task.id,
                        "title": task.title,
                        "agent": task.agent,
                        "description": task.description,
                    }
                    for task in project.tasks
                ],
                ensure_ascii=False,
            ),
        )
        context.shared_context = memory.sync_project_to_shared_context(
            project_id,
            dict(context.shared_context),
        )
        context.metadata["project_id"] = project_id

        if context.metadata.get("execute_tasks") and self._runtime:

            project = self._workflow.execute_tasks(
                project,
                self._runtime,
                session_id=context.session_id,
            )

        self.last_project = project

        model = "project_manager"

        if self._client is not None:

            model = getattr(self._client, "model", model)

        return AgentResult(
            success=True,
            model=model,
            content=self.format_task_list(project),
        )

    @staticmethod
    def format_task_list(project: SoftwareProject) -> str:

        lines = [
            f"# 项目：{project.name}",
            "",
            f"**项目 ID**: `{project.id}`",
            "",
            "## 目标理解",
            project.goal_summary,
            "",
            "## 任务列表",
            "",
        ]

        for index, task in enumerate(project.tasks, start=1):

            lines.extend(
                [
                    f"### {index}. {task.title}",
                    f"- **id**: `{task.id}`",
                    f"- **agent**: `{task.agent}`",
                    f"- **status**: `{task.status.value}`",
                    f"- **description**: {task.description}",
                ]
            )

            if task.result:

                preview = task.result[:200]

                if len(task.result) > 200:

                    preview += "..."

                lines.append(f"- **result**: {preview}")

            lines.append("")

        lines.append("## JSON")
        lines.append(
            json.dumps(
                project.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )

        return "\n".join(lines)
