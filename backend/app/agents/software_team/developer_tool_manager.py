"""Developer Agent 专用 ToolManager（仅 filesystem + code）。"""

from __future__ import annotations

from app.agents.software_team.tools.code_tool import CodeTool
from app.agents.software_team.tools.filesystem_tool import FileSystemTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult


class DeveloperToolManager:
    """
    限制 Developer Loop 只能调用 FileSystem / Code Tool。
    """

    def __init__(self) -> None:

        self._tools = {
            FileSystemTool().name: FileSystemTool(),
            CodeTool().name: CodeTool(),
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
                    f"Tool '{context.tool_name}' is not allowed. "
                    f"Use: {', '.join(sorted(self._tools))}"
                ),
            )

        return tool.execute(context)
