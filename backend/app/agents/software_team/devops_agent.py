"""
Phase 5.7：DevOps Agent — Dockerfile/compose、环境、Build/Deploy、Deployment Report。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.executor.agent_executor import AgentExecutor
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.agents.software_team.deployment_report import DeploymentReport
from app.agents.software_team.devops_prompt import DEFAULT_BUILD_CMD
from app.agents.software_team.devops_prompt import DEFAULT_DEPLOY_CMD
from app.agents.software_team.devops_prompt import DEPLOYMENT_REPORT_FILENAME
from app.agents.software_team.devops_prompt import render_devops_template
from app.agents.software_team.devops_tool_manager import DevOpsToolManager
from app.agents.software_team.tools.terminal_policy import terminal_mode_ctx
from app.agents.software_team.tools.workspace import developer_workspace_ctx
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.llm.types import Message
from app.tools.types import ToolContext


class DevOpsLLMClient(Protocol):
    model: str

    def bind_tool_manager(self, tool_manager) -> None: ...

    def chat(self, messages, use_tools: bool = True): ...


class DevOpsAgent(BaseAgent):
    __test__ = False

    ARTIFACT_RELATIVE_PATH = f"docs/{DEPLOYMENT_REPORT_FILENAME}"

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: DevOpsLLMClient | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client

        self.last_report: DeploymentReport | None = None
        self.build_command: str = DEFAULT_BUILD_CMD
        self.deploy_command: str = DEFAULT_DEPLOY_CMD

    @property
    def name(self) -> str:

        return "devops"

    def get_capabilities(self) -> list[str]:

        return [
            "software_team",
            "docker",
            "deploy",
            "environment",
        ]

    def before_run(
        self,
        context: AgentContext,
    ) -> None:

        workspace = self._resolve_workspace(context)

        if workspace is not None:

            workspace.mkdir(parents=True, exist_ok=True)
            developer_workspace_ctx.set(workspace)

        terminal_mode_ctx.set("devops")

        self.build_command = str(
            context.metadata.get("build_command")
            or context.shared_context.get("build_command")
            or DEFAULT_BUILD_CMD
        )

        self.deploy_command = str(
            context.metadata.get("deploy_command")
            or context.shared_context.get("deploy_command")
            or DEFAULT_DEPLOY_CMD
        )

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        workspace = developer_workspace_ctx.get()

        if workspace is None:

            return AgentResult(
                success=False,
                model="devops",
                content="Missing workspace_dir in metadata.",
            )

        simulate = bool(context.metadata.get("devops_simulate"))

        tool_manager = DevOpsToolManager()

        if self._client is None:

            self._bootstrap_deploy_files(tool_manager)

        else:

            self._client.bind_tool_manager(tool_manager)

            prompt = render_devops_template(
                architecture_excerpt=self._resolve_architecture(
                    context,
                    workspace,
                ),
                deploy_instruction=context.user_message.strip()
                or "Prepare Docker deployment.",
            )

            executor = AgentExecutor(
                client=self._client,
                config=self._config,
                tool_message_builder=ToolMessageBuilder(),
                tool_manager=tool_manager,
                error_handler=AgentErrorHandler(),
                tracer=AgentTracer(),
            )

            executor.run(
                AgentContext(
                    session_id=context.session_id,
                    user_message=context.user_message,
                    metadata=dict(context.metadata),
                    shared_context=dict(context.shared_context),
                    agent_name="devops",
                ),
                [Message(role="user", content=prompt)],
            )

        report = self._run_build_deploy(
            tool_manager,
            simulate=simulate or not _docker_available(),
        )

        self.last_report = report

        markdown = report.to_markdown()
        artifact_note = self._maybe_write_report(context, markdown)

        prefix = f"{artifact_note}\n\n" if artifact_note else ""

        return AgentResult(
            success=report.success,
            model="devops",
            content=prefix + markdown,
        )

    def _run_build_deploy(
        self,
        tool_manager: DevOpsToolManager,
        *,
        simulate: bool,
    ) -> DeploymentReport:

        workspace = developer_workspace_ctx.get()
        artifacts = []

        if workspace:

            for name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"):

                if (workspace / name).is_file():

                    artifacts.append(name)

        env_files = []

        if workspace:

            for path in workspace.rglob(".env.example"):

                env_files.append(str(path.relative_to(workspace)))

        if simulate:

            return DeploymentReport(
                success=True,
                artifacts=artifacts,
                environment_files=env_files,
                build_command=self.build_command,
                build_output="[simulated] docker compose build succeeded",
                deploy_command=self.deploy_command,
                deploy_output="[simulated] docker compose up -d succeeded",
                notes="Docker 不可用或 devops_simulate=true，已模拟 Build/Deploy。",
            )

        build_result = tool_manager.execute(
            ToolContext(
                tool_name="terminal",
                arguments={"command": self.build_command},
            )
        )

        deploy_result = tool_manager.execute(
            ToolContext(
                tool_name="terminal",
                arguments={"command": self.deploy_command},
            )
        )

        success = build_result.success and deploy_result.success

        return DeploymentReport(
            success=success,
            artifacts=artifacts,
            environment_files=env_files,
            build_command=self.build_command,
            build_output=build_result.content or "",
            deploy_command=self.deploy_command,
            deploy_output=deploy_result.content or "",
        )

    def _bootstrap_deploy_files(
        self,
        tool_manager: DevOpsToolManager,
    ) -> None:

        dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
"""

        compose = """services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.example
    healthcheck:
      test: ["CMD", "python", "-c", "print('ok')"]
      interval: 30s
      timeout: 5s
      retries: 3
"""

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "Dockerfile",
                    "content": dockerfile,
                },
            )
        )

        tool_manager.execute(
            ToolContext(
                tool_name="code",
                arguments={
                    "action": "write",
                    "path": "docker-compose.yml",
                    "content": compose,
                },
            )
        )

        tool_manager.execute(
            ToolContext(
                tool_name="environment",
                arguments={
                    "action": "write",
                    "path": ".env.example",
                    "content": (
                        "APP_ENV=development\n"
                        "DATABASE_URL=postgresql://user:pass@db:5432/app\n"
                        "SECRET_KEY=change-me\n"
                    ),
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

        target = Path(str(artifact_dir)) / DevOpsAgent.ARTIFACT_RELATIVE_PATH

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")

        return f"Deployment Report 已写入：`{target.resolve()}`"

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

                return str(context.shared_context[key])[:6000]

            if context.metadata.get(key):

                return str(context.metadata[key])[:6000]

        doc = workspace / "docs" / "architecture.md"

        if doc.is_file():

            return doc.read_text(encoding="utf-8")[:6000]

        return ""


def _docker_available() -> bool:

    return shutil.which("docker") is not None
