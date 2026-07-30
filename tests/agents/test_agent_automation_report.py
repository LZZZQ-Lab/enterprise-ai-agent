"""Task 8.2：生成 Agent Test Report 汇总。"""

from __future__ import annotations

from pathlib import Path

from tests.agents.report import AgentCaseResult
from tests.agents.report import AgentTestReport
from tests.agents.test_developer_agent import run_developer_agent_case
from tests.agents.test_manager_agent import run_manager_agent_case
from tests.agents.test_reviewer_agent import run_reviewer_agent_case
from tests.agents.test_tester_agent import run_tester_agent_case

REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "artifacts" / "agent_test_report.md"
)


def test_generate_agent_test_report(
    agent_team_config,
    user_request: str,
    tmp_path: Path,
) -> None:
    """串联四类 Agent 自动化用例并写入 Agent Test Report。"""

    report = AgentTestReport()

    for agent_name, runner, subdir in (
        ("ProjectManagerAgent", run_manager_agent_case, None),
        ("DeveloperAgent", run_developer_agent_case, "dev"),
        ("ReviewerAgent", run_reviewer_agent_case, "rev"),
        ("TesterAgent", run_tester_agent_case, "tester"),
    ):
        if subdir is None:
            payload = runner(user_request, agent_team_config)
        else:
            ws = tmp_path / subdir
            ws.mkdir()
            payload = runner(user_request, agent_team_config, ws)

        report.add(
            AgentCaseResult(
                agent=agent_name,
                user_request=user_request,
                success=payload["success"],
                flow_checks=payload["flow_checks"],
                tool_checks=payload["tool_checks"],
                workflow_checks=payload["workflow_checks"],
                format_checks=payload["format_checks"],
                notes=payload["notes"],
            )
        )

    report.write(REPORT_PATH)

    assert REPORT_PATH.is_file()
    assert report.all_passed is True

    text = REPORT_PATH.read_text(encoding="utf-8")

    for name in (
        "ProjectManagerAgent",
        "DeveloperAgent",
        "ReviewerAgent",
        "TesterAgent",
    ):
        assert name in text

    assert "**Overall**: PASS" in text
