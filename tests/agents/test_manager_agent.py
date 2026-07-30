"""Task 8.2：Project Manager Agent 自动化测试。"""

from __future__ import annotations

import json

from app.agents.software_team.manager_agent import ProjectManagerAgent
from app.agents.software_team.task import TaskStatus
from app.agents.types import AgentContext

from tests.agents.mocks import BlogPlanningMockLLM


def test_manager_agent_user_request_flow(
    agent_team_config,
    user_request: str,
) -> None:
    """模拟 User Request → PM 规划 → 任务列表。"""

    pm = ProjectManagerAgent(
        config=agent_team_config,
        client=BlogPlanningMockLLM(),
    )

    result = pm.run(
        AgentContext(
            session_id="agent-auto-pm",
            user_message=user_request,
        )
    )

    assert result.success is True
    assert pm.last_project is not None

    project = pm.last_project

    assert project.goal_summary
    assert len(project.tasks) >= 4

    agents = {task.agent for task in project.tasks}

    assert "developer" in agents
    assert "reviewer" in agents
    assert "tester" in agents

    for task in project.tasks:
        assert task.status == TaskStatus.PENDING
        assert task.title
        assert task.agent


def test_manager_agent_output_format(
    agent_team_config,
    user_request: str,
) -> None:
    """验证 PM 输出 Markdown + JSON 结构。"""

    pm = ProjectManagerAgent(
        config=agent_team_config,
        client=BlogPlanningMockLLM(),
    )

    result = pm.run(
        AgentContext(
            session_id="agent-auto-pm-fmt",
            user_message=user_request,
        )
    )

    content = result.content or ""

    assert "## 目标理解" in content
    assert "## 任务列表" in content
    assert "## JSON" in content
    assert "agent" in content

    json_start = content.index("## JSON") + len("## JSON")
    payload = json.loads(content[json_start:].strip())

    assert "tasks" in payload
    assert isinstance(payload["tasks"], list)


def run_manager_agent_case(user_request: str, config) -> dict:
    """供 Agent Test Report 聚合。"""

    pm = ProjectManagerAgent(config=config, client=BlogPlanningMockLLM())
    result = pm.run(
        AgentContext(session_id="report-pm", user_message=user_request)
    )
    project = pm.last_project

    return {
        "success": result.success,
        "flow_checks": {
            "execute_returns_success": result.success,
            "last_project_created": project is not None,
        },
        "tool_checks": {},
        "workflow_checks": {
            "tasks_pending": bool(project)
            and all(t.status == TaskStatus.PENDING for t in project.tasks),
            "goal_summary_set": bool(project and project.goal_summary),
        },
        "format_checks": {
            "markdown_sections": "## 任务列表" in (result.content or ""),
            "json_block": "## JSON" in (result.content or ""),
        },
        "notes": f"tasks={len(project.tasks) if project else 0}",
    }
