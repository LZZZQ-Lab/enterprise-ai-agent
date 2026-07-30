"""DevOps Agent ToolManager。"""

from __future__ import annotations

from app.agents.software_team.tools.code_tool import CodeTool
from app.agents.software_team.tools.environment_tool import EnvironmentTool
from app.agents.software_team.tools.filesystem_tool import FileSystemTool
from app.agents.software_team.tools.terminal_tool import TerminalTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class DevOpsToolManager:
    def __init__(self) -> None:

        self._tools = {
            FileSystemTool().name: FileSystemTool(),
            CodeTool().name: CodeTool(),
            EnvironmentTool().name: EnvironmentTool(),
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
