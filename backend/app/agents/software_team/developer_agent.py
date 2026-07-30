"""
Task 5.4：Developer Agent — Tool Loop 生成项目代码，记录变更历史。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.executor.agent_executor import AgentExecutor
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.agents.software_team.code_change_history import CodeChangeHistory
from app.agents.software_team.developer_prompt import HISTORY_RELATIVE_PATH
from app.agents.software_team.developer_prompt import format_task_list_for_prompt
from app.agents.software_team.developer_prompt import render_developer_template
from app.agents.software_team.developer_tool_manager import DeveloperToolManager
from app.agents.software_team.tools.code_tool import developer_history_ctx
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.llm.types import Message
from app.tools.types import ToolContext


class DeveloperLLMClient(Protocol):
    model: str

    def bind_tool_manager(self, tool_manager) -> None: ...

    def chat(self, messages, use_tools: bool = True): ...


class DeveloperAgent(BaseAgent):
    """
    读取架构与任务列表，经 filesystem/code Tool 生成代码。
    禁止 LLM 在正文中直接落盘；文件变更仅经 Tool。
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: DeveloperLLMClient | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client

        self._history = CodeChangeHistory()
        self.change_history: CodeChangeHistory = self._history

    @property
    def name(self) -> str:

        return "developer"

    def get_capabilities(self) -> list[str]:

        return [
            "software_team",
            "implementation",
            "filesystem_tool",
            "code_tool",
        ]

    def before_run(
        self,
        context: AgentContext,
    ) -> None:

        from app.memory.memory_manager import get_default_enterprise_memory_manager

        memory = get_default_enterprise_memory_manager()
        project_id = memory.resolve_project_id(
            session_id=context.session_id,
            metadata=context.metadata,
            shared_context=context.shared_context,
        )
        context.shared_context = memory.sync_project_to_shared_context(
            project_id,
            dict(context.shared_context),
        )
        context.metadata.setdefault("project_id", project_id)

        workspace = self._resolve_workspace(context)

        if workspace is not None:

            workspace.mkdir(parents=True, exist_ok=True)
            developer_workspace_ctx.set(workspace)

        self._history.session_id = context.session_id
        developer_history_ctx.set(self._history)

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        workspace = developer_workspace_ctx.get()

        if workspace is None:

            return AgentResult(
                success=False,
                model="developer",
                content="Missing workspace_dir in metadata.",
            )

        architecture = self._resolve_architecture(context, workspace)
        task_list = self._resolve_task_list(context)
        instruction = context.user_message.strip() or "Implement MVP from architecture and tasks."

        tool_manager = DeveloperToolManager()

        if self._client is None:

            summary = self._bootstrap_via_tools(
                tool_manager,
                instruction=instruction,
            )

            self._persist_history_file(tool_manager)

            body = (
                f"{summary}\n\n{self._history.to_markdown()}"
            )

            return AgentResult(
                success=True,
                model="tool_bootstrap",
                content=body,
            )

        self._client.bind_tool_manager(tool_manager)

        prompt = render_developer_template(
            architecture_excerpt=architecture,
            task_list_excerpt=task_list,
            dev_instruction=instruction,
        )

        messages = [
            Message(role="user", content=prompt),
        ]

        tracer = AgentTracer()
        executor = AgentExecutor(
            client=self._client,
            config=self._config,
            tool_message_builder=ToolMessageBuilder(),
            tool_manager=tool_manager,
            error_handler=AgentErrorHandler(),
            tracer=tracer,
        )

        loop_context = AgentContext(
            session_id=context.session_id,
            user_message=instruction,
            metadata=dict(context.metadata),
            shared_context=dict(context.shared_context),
            agent_name="developer",
        )

        result = executor.run(loop_context, messages)

        if result.content and _looks_like_direct_file_dump(result.content):

            result = AgentResult(
                success=False,
                model=result.model,
                content=(
                    "Rejected: assistant attempted to emit full file content "
                    "without tool calls. Use code/filesystem tools only."
                ),
            )

        if result.success:

            self._persist_history_file(tool_manager)

            result = AgentResult(
                success=True,
                model=result.model,
                content=(
                    f"{result.content}\n\n{self._history.to_markdown()}"
                ),
            )

        return result

    def _bootstrap_via_tools(
        self,
        tool_manager: DeveloperToolManager,
        *,
        instruction: str,
    ) -> str:

        _ = instruction

        readme = (
            "# Demo Project\n\n"
            "Generated by DeveloperAgent via code tool only.\n"
        )

        main_py = (
            '"""Application entrypoint."""\n\n'
            "def main() -> None:\n"
            '    print("Hello from software team MVP")\n\n\n'
            'if __name__ == "__main__":\n'
            "    main()\n"
        )

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "README.md",
                    "content": readme,
                },
            )
        )

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "src/main.py",
                    "content": main_py,
                },
            )
        )

        return (
            "Bootstrap complete via code tool: "
            "README.md, src/main.py"
        )

    def _persist_history_file(
        self,
        tool_manager: DeveloperToolManager,
    ) -> None:

        if not self._history.records:

            return

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": HISTORY_RELATIVE_PATH,
                    "content": self._history.to_jsonl(),
                },
            )
        )

    @staticmethod
    def _resolve_workspace(context: AgentContext) -> Path | None:

        raw = (
            context.metadata.get("workspace_dir")
            or context.metadata.get("artifact_dir")
            or context.shared_context.get("workspace_dir")
        )

        if not raw:

            return None

        return Path(str(raw))

    @staticmethod
    def _resolve_architecture(
        context: AgentContext,
        workspace: Path,
    ) -> str:

        for key in (
            "architecture",
            "architecture_md",
            "system_design",
        ):

            if context.shared_context.get(key):

                return str(context.shared_context[key])

            if context.metadata.get(key):

                return str(context.metadata[key])

        doc = workspace / "docs" / "architecture.md"

        if doc.is_file():

            return doc.read_text(encoding="utf-8")[:12000]

        return ""

    @staticmethod
    def _resolve_task_list(context: AgentContext) -> str:

        tasks = (
            context.shared_context.get("tasks")
            or context.shared_context.get("task_list")
            or context.metadata.get("tasks")
            or context.metadata.get("task_list")
        )

        if tasks is None:
            from app.memory.memory_manager import get_default_enterprise_memory_manager

            memory = get_default_enterprise_memory_manager()
            project_id = memory.resolve_project_id(
                session_id=context.session_id,
                metadata=context.metadata,
                shared_context=context.shared_context,
            )
            tasks = memory.project.get(project_id, "task_list")

        if tasks is not None:

            return format_task_list_for_prompt(tasks)

        return context.metadata.get("task_list_text", "")


def _looks_like_direct_file_dump(content: str) -> bool:

    if "```" in content and len(content) > 800:

        return True

    if re.search(
        r"(?m)^(?:def |class |import |from .+ import)",
        content,
    ) and len(content) > 600:

        return True

    return False
