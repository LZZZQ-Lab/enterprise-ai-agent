"""Task 8.2：Tester Agent 自动化测试。"""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.tester_agent import TesterAgent
from app.agents.types import AgentContext

from tests.agents.mocks import TesterToolMockLLM


def test_tester_agent_bootstrap_pytest_flow(
    agent_team_config,
    user_request: str,
    tmp_path: Path,
) -> None:
    """无 LLM bootstrap：生成样例测试并执行 pytest。"""

    agent = TesterAgent(
        config=agent_team_config,
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-test-boot",
            user_message=user_request,
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert result.success is True
    assert agent.last_report is not None
    assert agent.last_report.passed >= 1
    assert (tmp_path / "tests" / "test_unit_sample.py").is_file()


def test_tester_agent_mock_tool_flow(
    agent_team_config,
    tmp_path: Path,
) -> None:
    """Mock LLM 写测试 + terminal pytest。"""

    mock = TesterToolMockLLM()

    agent = TesterAgent(
        config=agent_team_config,
        client=mock,
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-test-mock",
            user_message="编写 API 测试",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert agent.last_report is not None
    assert "Test Report" in (result.content or "")

    md = agent.last_report.to_markdown()

    assert "# Test Report" in md
    assert "## 摘要" in md


def run_tester_agent_case(user_request: str, config, workspace: Path) -> dict:
    mock = TesterToolMockLLM()
    agent = TesterAgent(config=config, client=mock)

    result = agent.run(
        AgentContext(
            session_id="report-tester",
            user_message=user_request,
            metadata={"workspace_dir": str(workspace)},
        )
    )

    report = agent.last_report

    return {
        "success": result.success or (report is not None),
        "flow_checks": {
            "llm_tool_turn": mock.turn >= 1,
            "report_generated": report is not None,
        },
        "tool_checks": {
            "code_or_terminal_used": mock.turn >= 1,
        },
        "workflow_checks": {
            "pytest_executed": bool(report and report.command),
            "report_success_flag": bool(report and report.success),
        },
        "format_checks": {
            "test_report_markdown": bool(report)
            and "# Test Report" in report.to_markdown(),
            "content_mentions_report": "Test Report" in (result.content or ""),
        },
        "notes": (
            f"passed={report.passed if report else 0} "
            f"failed={report.failed if report else 0}"
        ),
    }
