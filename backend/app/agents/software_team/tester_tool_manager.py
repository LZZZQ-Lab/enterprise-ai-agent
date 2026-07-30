"""Tester Agent 专用 ToolManager。"""

from __future__ import annotations

from app.agents.software_team.tools.code_tool import CodeTool
from app.agents.software_team.tools.filesystem_tool import FileSystemTool
from app.agents.software_team.tools.terminal_tool import TerminalTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class TesterToolManager:
    """
    filesystem（读）+ code（写测试）+ terminal（跑 pytest）。
    """

    def __init__(self) -> None:

        self._tools = {
            FileSystemTool().name: FileSystemTool(),
            CodeTool().name: CodeTool(),
            TerminalTool().name: TerminalTool(),
        }

    def get_schemas(self) -> list[dict]:

        return [tool.schema for tool in self._tools.values()]

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        tool = self._tools.get(context.tool_name)

        if tool is None:

            return ToolResult(
                success=False,
                content=(
                    f"Tool '{context.tool_name}' not allowed. "
                    f"Use: {', '.join(sorted(self._tools))}"
                ),
            )

        return tool.execute(context)
