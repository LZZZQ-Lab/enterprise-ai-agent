"""MCP 生态：Adapter → ToolRegistry → Agent。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.mcp.adapter import adapt_client_tools
from app.mcp.client import EnterpriseDemoMCPClient
from app.mcp.tools import setup_enterprise_mcp_demo
from app.tools.registry import ToolRegistry
from app.tools.types import ToolContext

WORKSPACE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "mcp_demo"
    / "workspace"
)


@pytest.fixture(autouse=True)
def _clear_mcp_registry_tools() -> None:
    """避免 MCP Tool 污染其它测试。"""

    names = [
        key
        for key in ToolRegistry._tools
        if key.startswith("enterprise-demo.")
    ]

    for name in names:

        ToolRegistry._tools.pop(name, None)

    yield

    for name in names:

        ToolRegistry._tools.pop(name, None)


def test_enterprise_demo_mcp_filesystem_db_git() -> None:

    client = EnterpriseDemoMCPClient(
        workspace_root=WORKSPACE,
    )

    client.connect()

    fs = client.call_tool(
        "fs_read_file",
        {"path": "docs/project_brief.txt"},
    )

    assert fs.success
    assert "Enterprise AI Agent Platform" in fs.content

    db = client.call_tool(
        "db_query",
        {"sql": "select * from projects"},
    )

    assert db.success
    assert "P-001" in db.content

    git = client.call_tool(
        "git_status",
        {"repo_path": "enterprise-ai-agent"},
    )

    assert git.success
    assert "branch main" in git.content


def test_adapter_produces_internal_tools() -> None:

    client = EnterpriseDemoMCPClient(
        workspace_root=WORKSPACE,
    )

    client.connect()

    tools = adapt_client_tools(client)

    assert len(tools) >= 5

    names = {tool.name for tool in tools}

    assert "enterprise-demo.fs_read_file" in names


def test_sync_to_tool_registry_and_execute() -> None:

    bridge = setup_enterprise_mcp_demo(
        workspace_root=WORKSPACE,
    )

    tool_name = "enterprise-demo.fs_read_file"

    tool = ToolRegistry.get(tool_name)

    result = tool.execute(
        ToolContext(
            tool_name=tool_name,
            arguments={
                "path": "docs/project_brief.txt",
            },
        )
    )

    assert result.success
    assert "制造业" in result.content
