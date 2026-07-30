"""Tool 调用测试。"""

from __future__ import annotations

from app.config import AgentConfig
from app.tools.factory import ToolFactory
from app.tools.manager import ToolManager
from app.tools.registry import ToolRegistry
from app.tools.time_tool import TimeTool
from app.tools.types import ToolContext


def test_tool_registry_registers_time_tool() -> None:

    ToolFactory.initialize()

    tool = ToolRegistry.get("time")

    assert isinstance(tool, TimeTool)
    assert tool.name == "time"


def test_tool_schema_available() -> None:

    ToolFactory.initialize()

    schemas = ToolRegistry.get_schemas()
    tool_names = [
        schema.get("function", {}).get("name")
        for schema in schemas
    ]

    assert "time" in tool_names


def test_time_tool_execute() -> None:

    tool = ToolFactory.get("time")

    result = tool.execute(
        ToolContext(
            tool_name="time",
            arguments={},
        ),
    )

    assert result.success is True
    assert result.content
    assert "-" in result.content


def test_tool_manager_executes_time_tool(
    agent_config: AgentConfig,
) -> None:

    manager = ToolManager(config=agent_config)

    result = manager.execute(
        ToolContext(
            tool_name="time",
            arguments={},
        ),
    )

    assert result.success is True
    assert result.content


def test_tool_manager_exposes_schemas(
    agent_config: AgentConfig,
) -> None:

    manager = ToolManager(config=agent_config)
    schemas = manager.get_schemas()

    assert isinstance(schemas, list)
    assert len(schemas) >= 1

    assert any(
        schema.get("function", {}).get("name") == "time"
        for schema in schemas
    )
