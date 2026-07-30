"""Task 5.6 Tester Agent tests."""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.test_report import parse_pytest_output
from app.agents.software_team.tester_agent import TesterAgent
from app.agents.software_team.tester_prompt import render_tester_template
from app.agents.software_team.tools.terminal_tool import TerminalTool
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.prompts.manager import TESTER_PROMPT_ID
from app.prompts.manager import get_default_prompt_manager
from app.tools.types import ToolContext


def test_tester_template_exists() -> None:

    text = get_default_prompt_manager().render(TESTER_PROMPT_ID)

    assert "{test_instruction}" in text


def test_parse_pytest_output() -> None:

    report = parse_pytest_output(
        "exit_code=0\n....\n2 passed in 0.01s",
        command="pytest",
    )

    assert report.passed == 2
    assert report.success


def test_terminal_rejects_shell_injection(tmp_path: Path) -> None:

    developer_workspace_ctx.set(tmp_path)
    tool = TerminalTool()

    result = tool.execute(
        ToolContext(
            tool_name="terminal",
            arguments={"command": "pytest; rm -rf /"},
        )
    )

    assert not result.success


def test_tester_bootstrap_runs_pytest(tmp_path: Path) -> None:

    agent = TesterAgent(
        config=AgentConfig(enable_trace=False),
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="test",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert result.success
    assert agent.last_report is not None
    assert agent.last_report.passed >= 2
    assert (tmp_path / "tests" / "test_unit_sample.py").is_file()


def test_tester_with_mock_llm(tmp_path: Path) -> None:

    from app.llm.types import ChatResult
    from app.llm.types import ToolCall

    class MockLLM:
        model = "m"
        n = 0

        def bind_tool_manager(self, tool_manager) -> None:

            pass

        def chat(self, messages, use_tools=True):

            self.n += 1

            if self.n == 1:

                return ChatResult(
                    model=self.model,
                    tool_calls=[
                        ToolCall(
                            id="1",
                            name="code",
                            arguments={
                                "action": "write",
                                "path": "tests/test_x.py",
                                "content": "def test_x():\n    assert 1\n",
                            },
                        ),
                    ],
                )

            return ChatResult(model=self.model, content="done")

    agent = TesterAgent(
        config=AgentConfig(max_iterations=3, enable_trace=False),
        client=MockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="write tests",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert agent.last_report is not None
    assert "Test Report" in result.content
