"""Task 5.7 DevOps Agent tests."""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.devops_agent import DevOpsAgent
from app.agents.software_team.devops_prompt import DEVOPS_TEMPLATE_NAME
from app.agents.software_team.devops_tool_manager import DevOpsToolManager
from app.agents.software_team.tools.environment_tool import EnvironmentTool
from app.agents.software_team.tools.terminal_policy import terminal_mode_ctx
from app.agents.software_team.tools.terminal_tool import TerminalTool
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.prompts.context import load_template
from app.tools.types import ToolContext


def test_devops_template() -> None:

    assert "{deploy_instruction}" in load_template(DEVOPS_TEMPLATE_NAME)


def test_environment_rejects_dotenv(tmp_path: Path) -> None:

    developer_workspace_ctx.set(tmp_path)
    tool = EnvironmentTool()

    result = tool.execute(
        ToolContext(
            tool_name="environment",
            arguments={
                "action": "write",
                "path": ".env",
                "content": "SECRET=1",
            },
        )
    )

    assert not result.success


def test_terminal_devops_mode_allows_compose(tmp_path: Path) -> None:

    developer_workspace_ctx.set(tmp_path)
    terminal_mode_ctx.set("devops")
    tool = TerminalTool()

    result = tool.execute(
        ToolContext(
            tool_name="terminal",
            arguments={"command": "docker compose config"},
        )
    )

    assert "Only pytest" not in result.content


def test_devops_bootstrap_simulate(tmp_path: Path) -> None:

    agent = DevOpsAgent(
        config=AgentConfig(enable_trace=False),
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="deploy",
            metadata={
                "workspace_dir": str(tmp_path),
                "devops_simulate": True,
            },
        )
    )

    assert result.success
    assert (tmp_path / "Dockerfile").is_file()
    assert (tmp_path / "docker-compose.yml").is_file()
    assert (tmp_path / ".env.example").is_file()
    assert agent.last_report is not None
    assert "Deployment Report" in result.content


def test_devops_tool_manager_has_environment() -> None:

    manager = DevOpsToolManager()
    names = {schema["function"]["name"] for schema in manager.get_schemas()}

    assert "environment" in names
    assert "terminal" in names
