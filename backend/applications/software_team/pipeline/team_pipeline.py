"""
Task 5.8：AI 软件团队端到端流水线。
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.software_team.manager_agent import ProjectManagerAgent
from app.agents.software_team.task import SoftwareProject
from app.agents.types import AgentContext
from app.config import AgentConfig

from applications.software_team.pipeline.demo_clients import (
    UserManagementArchitectureMockLLM,
)
from applications.software_team.pipeline.demo_clients import (
    UserManagementPMMockLLM,
)
from applications.software_team.pipeline.demo_clients import (
    UserManagementProductMockLLM,
)
from applications.software_team.pipeline.run_record import RunRecorder


DEFAULT_REQUIREMENT = "开发一个用户管理系统"


class SoftwareTeamPipeline:
    """
    Manager → Product → Architecture → Developer → Reviewer → Tester → DevOps
    """

    def __init__(
        self,
        *,
        runs_base_dir: Path,
        config: AgentConfig | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:

        self._runs_base = Path(runs_base_dir)
        self._config = config or AgentConfig(
            max_iterations=6,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        )
        self._runtime = runtime or AgentRuntime(default_config=self._config)

        self.last_recorder: RunRecorder | None = None
        self.last_project: SoftwareProject | None = None

    def run(
        self,
        requirement: str,
        *,
        session_id: str = "full-team-demo",
    ) -> Path:

        recorder = RunRecorder(self._runs_base)
        self.last_recorder = recorder

        workspace = recorder.workspace_dir
        shared: dict[str, Any] = {}

        project = self._stage_manager(
            recorder,
            requirement,
            session_id,
        )

        self.last_project = project
        recorder.save_tasks(project)

        shared["project_name"] = project.name
        shared["goal_summary"] = project.goal_summary
        shared["tasks"] = [task.to_dict() for task in project.tasks]

        prd = self._stage_runtime(
            recorder,
            stage="02_product",
            agent="product",
            session_id=session_id,
            user_message=requirement,
            shared=shared,
            agent_kwargs={"client": UserManagementProductMockLLM()},
            report_name="prd",
            report_file="PRD.md",
        )

        shared["prd"] = prd
        (workspace / "docs").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "PRD.md").write_text(prd, encoding="utf-8")

        arch = self._stage_runtime(
            recorder,
            stage="03_architecture",
            agent="architecture",
            session_id=session_id,
            user_message=prd,
            shared=shared,
            metadata={"artifact_dir": str(workspace)},
            agent_kwargs={"client": UserManagementArchitectureMockLLM()},
            report_name="architecture",
            report_file="architecture.md",
        )

        shared["architecture"] = arch

        dev_summary = self._stage_runtime(
            recorder,
            stage="04_developer",
            agent="developer",
            session_id=session_id,
            user_message="实现用户管理系统 MVP：用户 API 与鉴权占位",
            shared=shared,
            metadata={
                "workspace_dir": str(workspace),
                "artifact_dir": str(workspace),
            },
            agent_kwargs={"client": None},
            report_name="developer",
            report_file="developer_summary.md",
        )

        shared["developer_summary"] = dev_summary

        git_diff = _collect_git_diff(workspace)

        review = self._stage_runtime(
            recorder,
            stage="05_reviewer",
            agent="reviewer",
            session_id=session_id,
            user_message=git_diff[:500] or "review",
            shared=shared,
            metadata={
                "git_diff": git_diff,
                "artifact_dir": str(recorder.reports_dir),
            },
            agent_kwargs={"client": None},
            report_name="review",
            report_file="REVIEW_REPORT.md",
        )

        shared["review_report"] = review

        test_report = self._stage_runtime(
            recorder,
            stage="06_tester",
            agent="tester",
            session_id=session_id,
            user_message="为用户管理系统编写并运行测试",
            shared=shared,
            metadata={
                "workspace_dir": str(workspace),
                "artifact_dir": str(recorder.reports_dir),
            },
            agent_kwargs={"client": None},
            report_name="test",
            report_file="TEST_REPORT.md",
        )

        shared["test_report"] = test_report

        deploy_report = self._stage_runtime(
            recorder,
            stage="07_devops",
            agent="devops",
            session_id=session_id,
            user_message="构建 Docker 镜像并部署用户管理系统",
            shared=shared,
            metadata={
                "workspace_dir": str(workspace),
                "artifact_dir": str(recorder.reports_dir),
                "devops_simulate": True,
            },
            agent_kwargs={"client": None},
            report_name="deployment",
            report_file="DEPLOYMENT_REPORT.md",
        )

        shared["deployment_report"] = deploy_report

        recorder.write_manifest(
            requirement=requirement,
            extra={"session_id": session_id},
        )

        return recorder.run_root

    def _stage_manager(
        self,
        recorder: RunRecorder,
        requirement: str,
        session_id: str,
    ) -> SoftwareProject:

        started = datetime.now(timezone.utc)

        pm = ProjectManagerAgent(
            config=self._config,
            client=UserManagementPMMockLLM(),
        )

        result = pm.run(
            AgentContext(
                session_id=session_id,
                user_message=requirement,
                agent_name="project_manager",
            )
        )

        project = pm.last_project

        if project is None:

            raise RuntimeError("Manager did not produce a project.")

        recorder.log_stage(
            stage="01_manager",
            agent="project_manager",
            success=result.success,
            model=result.model,
            content=result.content,
            started_at=started,
        )

        recorder.save_report(
            "manager_task_list",
            result.content,
            filename="MANAGER_TASK_LIST.md",
        )

        return project

    def _stage_runtime(
        self,
        recorder: RunRecorder,
        *,
        stage: str,
        agent: str,
        session_id: str,
        user_message: str,
        shared: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        agent_kwargs: dict[str, Any] | None = None,
        report_name: str,
        report_file: str,
    ) -> str:

        started = datetime.now(timezone.utc)

        meta = dict(metadata or {})

        result = self._runtime.run(
            AgentTask(
                session_id=session_id,
                user_message=user_message,
                agent_name=agent,
                shared_context=dict(shared),
                metadata=meta,
            ),
            config=self._config,
            **(agent_kwargs or {}),
        )

        content = result.content or ""

        recorder.log_stage(
            stage=stage,
            agent=agent,
            success=result.success,
            model=result.model,
            content=content,
            started_at=started,
        )

        recorder.save_report(report_name, content, filename=report_file)

        return content


def _collect_git_diff(workspace: Path) -> str:

    synthetic = _synthetic_diff(workspace)

    if not workspace.is_dir():

        return synthetic

    try:

        subprocess.run(
            ["git", "init"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        subprocess.run(
            [
                "git",
                "-c",
                "user.email=demo@local",
                "-c",
                "user.name=Demo",
                "commit",
                "-m",
                "demo",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        completed = subprocess.run(
            ["git", "show", "--format=", "--patch", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        stdout = completed.stdout or ""

        if stdout.strip():

            return stdout

    except (OSError, subprocess.SubprocessError):

        pass

    return synthetic


def _synthetic_diff(workspace: Path) -> str:

    chunks: list[str] = []

    if not workspace.exists():

        return ""

    for path in sorted(workspace.rglob("*")):

        if not path.is_file():

            continue

        if ".git" in path.parts:

            continue

        rel = path.relative_to(workspace).as_posix()

        if rel.startswith("docs/") and rel.endswith(".md"):

            continue

        try:

            text = path.read_text(encoding="utf-8")

        except UnicodeDecodeError:

            continue

        chunks.append(f"diff --git a/{rel} b/{rel}\n")
        chunks.append(f"--- a/{rel}\n+++ b/{rel}\n")

        for line in text.splitlines():

            chunks.append(f"+{line}\n")

    return "".join(chunks)
