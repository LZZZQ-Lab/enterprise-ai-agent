"""Task 5.1 Project Manager Agent tests."""

from __future__ import annotations

import json

from app.agents.software_team.manager_agent import ProjectManagerAgent
from app.agents.software_team.task import SoftwareTeamTask
from app.agents.software_team.task import TaskStatus
from app.agents.software_team.workflow import SoftwareTeamWorkflow
from app.agents.software_team.workflow import _extract_json_array
from app.agents.types import AgentContext
from app.config import AgentConfig


class MockPlanner:
    model = "mock"

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        text = messages[-1].content or ""

        if "_GOAL" in text:

            return ChatResult(
                model=self.model,
                content="构建库存管理 API",
            )

        payload = [
            {
                "title": "PRD",
                "description": "写 PRD",
                "agent": "product",
            },
            {
                "title": "实现 API",
                "description": "写代码",
                "agent": "developer",
            },
        ]

        return ChatResult(
            model=self.model,
            content=json.dumps(payload),
        )


def test_extract_json_array_from_fence() -> None:

    raw = '```json\n[{"title":"a","agent":"product"}]\n```'

    data = _extract_json_array(raw)

    assert len(data) == 1


def test_workflow_plan_tasks_from_llm() -> None:

    workflow = SoftwareTeamWorkflow(client=MockPlanner())

    tasks = workflow.plan_tasks(
        "做一个库存系统",
        "库存 API",
    )

    assert len(tasks) == 2
    assert tasks[0].agent == "product"
    assert tasks[0].status == TaskStatus.PENDING


def test_pm_agent_blog_demo_style() -> None:

    from applications.software_team.run_pm_demo import BlogDemoMockLLM

    pm = ProjectManagerAgent(
        config=AgentConfig(enable_trace=False),
        client=BlogDemoMockLLM(),
    )

    result = pm.run(
        AgentContext(
            session_id="test",
            user_message="开发一个博客系统",
        )
    )

    assert result.success
    assert pm.last_project is not None
    assert len(pm.last_project.tasks) >= 4

    agents = {task.agent for task in pm.last_project.tasks}

    assert "product" in agents
    assert "developer" in agents

    assert "任务列表" in result.content


def test_task_to_dict_roundtrip() -> None:

    task = SoftwareTeamTask(
        title="T",
        description="D",
        agent="tester",
    )

    restored = SoftwareTeamTask.from_dict(task.to_dict())

    assert restored.title == "T"
    assert restored.agent == "tester"
