"""
Phase 5.6：Tester Agent — 生成测试、terminal 跑 pytest、输出 Test Report。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.executor.agent_executor import AgentExecutor
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.agents.software_team.test_report import TestReport
from app.agents.software_team.test_report import parse_pytest_output
from app.agents.software_team.tester_prompt import DEFAULT_PYTEST_CMD
from app.agents.software_team.tester_prompt import TEST_REPORT_FILENAME
from app.agents.software_team.tester_prompt import render_tester_template
from app.agents.software_team.tester_tool_manager import TesterToolManager
from app.agents.software_team.tools.terminal_policy import terminal_mode_ctx
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.llm.types import Message
from app.tools.types import ToolContext


class TesterLLMClient(Protocol):
    model: str

    def bind_tool_manager(self, tool_manager) -> None: ...

    def chat(self, messages, use_tools: bool = True): ...


class TesterAgent(BaseAgent):
    """
    生成 Unit/API 测试（code Tool）→ terminal 执行 pytest → Test Report。
    """

    __test__ = False

    ARTIFACT_RELATIVE_PATH = f"docs/{TEST_REPORT_FILENAME}"

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: TesterLLMClient | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client

        self.last_report: TestReport | None = None
        self.pytest_command: str = DEFAULT_PYTEST_CMD

    @property
    def name(self) -> str:

        return "tester"

    def get_capabilities(self) -> list[str]:

        return [
            "software_team",
            "unit_test",
            "api_test",
            "terminal_tool",
            "pytest",
        ]

    def before_run(
        self,
        context: AgentContext,
    ) -> None:

        workspace = self._resolve_workspace(context)

        if workspace is not None:

            workspace.mkdir(parents=True, exist_ok=True)
            developer_workspace_ctx.set(workspace)

        terminal_mode_ctx.set("pytest")

        self.pytest_command = str(
            context.metadata.get("pytest_command")
            or context.shared_context.get("pytest_command")
            or DEFAULT_PYTEST_CMD
        )

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        workspace = developer_workspace_ctx.get()

        if workspace is None:

            return AgentResult(
                success=False,
                model="tester",
                content="Missing workspace_dir in metadata.",
            )

        tool_manager = TesterToolManager()

        if self._client is None:

            self._bootstrap_tests(tool_manager)

        else:

            self._client.bind_tool_manager(tool_manager)

            prompt = render_tester_template(
                architecture_excerpt=self._resolve_architecture(
                    context,
                    workspace,
                ),
                source_hint=self._resolve_source_hint(context, workspace),
                test_instruction=context.user_message.strip()
                or "Generate unit and API tests, run pytest.",
            )

            messages = [Message(role="user", content=prompt)]

            executor = AgentExecutor(
                client=self._client,
                config=self._config,
                tool_message_builder=ToolMessageBuilder(),
                tool_manager=tool_manager,
                error_handler=AgentErrorHandler(),
                tracer=AgentTracer(),
            )

            loop_context = AgentContext(
                session_id=context.session_id,
                user_message=context.user_message,
                metadata=dict(context.metadata),
                shared_context=dict(context.shared_context),
                agent_name="tester",
            )

            executor.run(loop_context, messages)

        report = self._run_pytest(tool_manager)
        self.last_report = report

        markdown = report.to_markdown()
        artifact_note = self._maybe_write_report(context, markdown)

        prefix = f"{artifact_note}\n\n" if artifact_note else ""

        return AgentResult(
            success=report.success,
            model="tester",
            content=prefix + markdown,
        )

    def _run_pytest(
        self,
        tool_manager: TesterToolManager,
    ) -> TestReport:

        cmd = self.pytest_command

        if cmd.strip().startswith("python "):

            cmd = cmd.replace("python", sys.executable, 1)

        if cmd.strip().startswith("pytest "):

            cmd = f"{sys.executable} -m {cmd}"

        result = tool_manager.execute(
            ToolContext(
                tool_name="terminal",
                arguments={"command": cmd},
            )
        )

        return parse_pytest_output(
            result.content or "",
            command=cmd,
        )

    def _bootstrap_tests(
        self,
        tool_manager: TesterToolManager,
    ) -> None:

        workspace = developer_workspace_ctx.get()

        if workspace is None:

            return

        (workspace / "tests").mkdir(parents=True, exist_ok=True)

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "tests/__init__.py",
                    "content": "",
                },
            )
        )

        unit = '''"""Unit tests (bootstrap)."""


def test_sample_unit_math():
    assert 1 + 1 == 2
'''

        api = '''"""API tests (bootstrap)."""


def test_sample_api_route_contract():
    route = "/api/v1/health"
    assert route.startswith("/api/v1")
'''

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "tests/test_unit_sample.py",
                    "content": unit,
                },
            )
        )

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "tests/test_api_sample.py",
                    "content": api,
                },
            )
        )

    @staticmethod
    def _maybe_write_report(
        context: AgentContext,
        markdown: str,
    ) -> str:

        artifact_dir = context.metadata.get("artifact_dir")

        if not artifact_dir:

            return ""

        target = Path(str(artifact_dir)) / TesterAgent.ARTIFACT_RELATIVE_PATH

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")

        return f"Test Report 已写入：`{target.resolve()}`"

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

        for key in ("architecture", "architecture_md"):

            if context.shared_context.get(key):

                return str(context.shared_context[key])[:8000]

            if context.metadata.get(key):

                return str(context.metadata[key])[:8000]

        doc = workspace / "docs" / "architecture.md"

        if doc.is_file():

            return doc.read_text(encoding="utf-8")[:8000]

        return ""

    @staticmethod
    def _resolve_source_hint(
        context: AgentContext,
        workspace: Path,
    ) -> str:

        hint = context.metadata.get("source_hint") or context.shared_context.get(
            "source_hint"
        )

        if hint:

            return str(hint)

        parts: list[str] = []

        for pattern in ("src/**/*.py", "app/**/*.py"):

            for path in list(workspace.glob(pattern))[:8]:

                parts.append(str(path.relative_to(workspace)))

        return "\n".join(parts) if parts else ""
