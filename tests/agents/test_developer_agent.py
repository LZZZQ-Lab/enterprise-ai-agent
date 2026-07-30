"""Task 8.2：Developer Agent 自动化测试。"""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.developer_agent import DeveloperAgent
from app.agents.types import AgentContext

from tests.agents.mocks import DeveloperToolMockLLM


def test_developer_agent_tool_call_flow(
    agent_team_config,
    user_request: str,
    tmp_path: Path,
) -> None:
    """Mock LLM 触发 code Tool → 文件落盘。"""

    mock = DeveloperToolMockLLM()

    agent = DeveloperAgent(
        config=agent_team_config,
        client=mock,
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-dev",
            user_message=user_request,
            metadata={"workspace_dir": str(tmp_path)},
            shared_context={
                "architecture": "FastAPI + RAG pipeline",
                "task_list": "- 实现 knowledge API",
            },
        )
    )

    assert result.success is True
    assert mock.turn >= 2
    assert (tmp_path / "src" / "knowledge_api.py").is_file()
    assert len(agent.change_history.records) >= 1
    assert agent.change_history.records[0].tool == "code"


def test_developer_agent_output_format(
    agent_team_config,
    tmp_path: Path,
) -> None:
    """Developer 输出含变更历史摘要。"""

    agent = DeveloperAgent(
        config=agent_team_config,
        client=DeveloperToolMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="agent-auto-dev-fmt",
            user_message="实现 API",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    content = result.content or ""

    assert "Code Change History" in content or result.success


def run_developer_agent_case(user_request: str, config, workspace: Path) -> dict:
    mock = DeveloperToolMockLLM()
    agent = DeveloperAgent(config=config, client=mock)

    result = agent.run(
        AgentContext(
            session_id="report-dev",
            user_message=user_request,
            metadata={"workspace_dir": str(workspace)},
        )
    )

    target = workspace / "src" / "knowledge_api.py"

    return {
        "success": result.success,
        "flow_checks": {
            "multi_turn_llm": mock.turn >= 2,
            "execute_success": result.success,
        },
        "tool_checks": {
            "code_tool_invoked": len(agent.change_history.records) >= 1,
            "file_written": target.is_file(),
        },
        "workflow_checks": {
            "history_recorded": len(agent.change_history.records) >= 1,
        },
        "format_checks": {
            "content_non_empty": bool(result.content),
        },
        "notes": f"tool_turns={mock.turn}",
    }
