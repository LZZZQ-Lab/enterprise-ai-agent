"""Task 5.4 Developer Agent tests."""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.code_change_history import CodeChangeHistory
from app.agents.software_team.developer_agent import DeveloperAgent
from app.agents.software_team.developer_prompt import HISTORY_RELATIVE_PATH
from app.agents.software_team.developer_tool_manager import DeveloperToolManager
from app.agents.software_team.tools.code_tool import developer_history_ctx
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.llm.types import ChatResult
from app.llm.types import ToolCall
from app.tools.types import ToolContext


def test_code_tool_records_history(tmp_path: Path) -> None:

    developer_workspace_ctx.set(tmp_path)

    history = CodeChangeHistory(session_id="s1")
    developer_history_ctx.set(history)

    manager = DeveloperToolManager()

    manager.execute(
        ToolContext(
            tool_name="code",
            arguments={
                "action": "write",
                "path": "src/a.py",
                "content": "x = 1\n",
            },
        )
    )

    assert len(history.records) == 1
    assert history.records[0].tool == "code"
    assert (tmp_path / "src" / "a.py").read_text(encoding="utf-8") == "x = 1\n"


def test_filesystem_read_only_no_write(tmp_path: Path) -> None:

    developer_workspace_ctx.set(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text(
        "arch",
        encoding="utf-8",
    )

    manager = DeveloperToolManager()

    read = manager.execute(
        ToolContext(
            tool_name="filesystem",
            arguments={
                "action": "read",
                "path": "docs/architecture.md",
            },
        )
    )

    assert read.success
    assert read.content == "arch"


def test_developer_bootstrap_without_llm(tmp_path: Path) -> None:

    agent = DeveloperAgent(
        config=AgentConfig(enable_trace=False),
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="build",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert result.success
    assert (tmp_path / "src" / "main.py").is_file()
    assert len(agent.change_history.records) >= 2
    assert (tmp_path / HISTORY_RELATIVE_PATH).is_file()


class RejectDumpLLM:
    model = "mock"

    def bind_tool_manager(self, tool_manager) -> None:

        self._tm = tool_manager

    def chat(self, messages, use_tools=True):

        return ChatResult(
            model=self.model,
            content="```python\n" + ("def f():\n    pass\n" * 80),
        )


def test_rejects_direct_file_dump_in_message(tmp_path: Path) -> None:

    agent = DeveloperAgent(
        config=AgentConfig(max_iterations=1, enable_trace=False),
        client=RejectDumpLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="implement",
            metadata={"workspace_dir": str(tmp_path)},
        )
    )

    assert not result.success
    assert "tool" in result.content.lower()


class TwoStepLLM:
    model = "mock"
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
                            "path": "main.py",
                            "content": "# ok\n",
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content="Done via tools.",
        )


def test_developer_loop_uses_code_tool(tmp_path: Path) -> None:

    agent = DeveloperAgent(
        config=AgentConfig(max_iterations=3, enable_trace=False),
        client=TwoStepLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="implement",
            metadata={"workspace_dir": str(tmp_path)},
            shared_context={"architecture": "FastAPI"},
        )
    )

    assert result.success
    assert (tmp_path / "main.py").is_file()
    assert "Code Change History" in result.content
