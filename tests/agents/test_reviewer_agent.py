"""Task 8.2：Reviewer Agent 自动化测试。"""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.reviewer_agent import ReviewerAgent
from app.agents.types import AgentContext
from app.config import AgentConfig

from tests.agents.mocks import SAMPLE_GIT_DIFF
from tests.agents.mocks import ReviewerStructuredMockLLM


def test_reviewer_agent_heuristic_flow(user_request: str) -> None:
    """无 LLM：启发式审查流程。"""

    agent = ReviewerAgent(
        config=AgentConfig(enable_trace=False, enable_rag=False),
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-rev-h",
            user_message=user_request,
            metadata={"git_diff": SAMPLE_GIT_DIFF},
        )
    )

    assert result.success is True
    assert agent.last_report is not None
    assert len(agent.last_report.findings) >= 1

    md = agent.last_report.to_markdown()

    assert "Code Review Report" in md
    assert "安全问题" in md


def test_reviewer_agent_mock_llm_flow(
    agent_team_config,
    user_request: str,
    tmp_path: Path,
) -> None:
    """Mock LLM 结构化 Review Report。"""

    agent = ReviewerAgent(
        config=agent_team_config,
        client=ReviewerStructuredMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-rev-llm",
            user_message=user_request,
            metadata={
                "git_diff": SAMPLE_GIT_DIFF,
                "artifact_dir": str(tmp_path),
            },
        )
    )

    assert result.success is True
    assert agent.last_report is not None
    assert agent.last_report_markdown

    report_path = tmp_path / "docs" / "REVIEW_REPORT.md"

    assert report_path.is_file()


def run_reviewer_agent_case(user_request: str, config, workspace: Path) -> dict:
    agent = ReviewerAgent(config=config, client=ReviewerStructuredMockLLM())

    result = agent.run(
        AgentContext(
            session_id="report-reviewer",
            user_message=user_request,
            metadata={
                "git_diff": SAMPLE_GIT_DIFF,
                "artifact_dir": str(workspace),
            },
        )
    )

    report = agent.last_report

    return {
        "success": result.success,
        "flow_checks": {
            "execute_success": result.success,
            "report_object_set": report is not None,
        },
        "tool_checks": {},
        "workflow_checks": {
            "report_object_set": report is not None,
            "artifact_written": (workspace / "docs" / "REVIEW_REPORT.md").is_file(),
            "summary_set": bool(report and report.summary),
        },
        "format_checks": {
            "markdown_title": "Code Review Report"
            in (report.to_markdown() if report else ""),
            "summary_section": "## 摘要" in (agent.last_report_markdown or ""),
        },
        "notes": f"summary={'yes' if report and report.summary else 'no'}",
    }
