"""
Task 5.8：project_runs 运行记录持久化。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.agents.software_team.task import SoftwareProject


@dataclass
class StageLogEntry:
    stage: str
    agent: str
    success: bool
    model: str
    started_at: str
    finished_at: str
    content_preview: str = ""

    def to_dict(self) -> dict:

        return asdict(self)


@dataclass
class RunRecorder:
    run_root: Path
    run_id: str = field(default_factory=lambda: uuid4().hex[:12])
    stages: list[StageLogEntry] = field(default_factory=list)

    def __post_init__(self) -> None:

        self.run_root = Path(self.run_root) / self.run_id
        self.logs_dir = self.run_root / "logs"
        self.reports_dir = self.run_root / "reports"
        self.workspace_dir = self.run_root / "workspace"

        for path in (
            self.run_root,
            self.logs_dir,
            self.reports_dir,
            self.workspace_dir,
        ):

            path.mkdir(parents=True, exist_ok=True)

    def save_tasks(
        self,
        project: SoftwareProject,
    ) -> Path:

        target = self.run_root / "tasks.json"
        payload = project.to_dict()

        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return target

    def save_report(
        self,
        name: str,
        content: str,
        *,
        filename: str | None = None,
    ) -> Path:

        safe = filename or f"{name}.md"
        target = self.reports_dir / safe
        target.write_text(content, encoding="utf-8")

        return target

    def log_stage(
        self,
        *,
        stage: str,
        agent: str,
        success: bool,
        model: str,
        content: str,
        started_at: datetime,
    ) -> None:

        finished = datetime.now(timezone.utc)
        entry = StageLogEntry(
            stage=stage,
            agent=agent,
            success=success,
            model=model,
            started_at=started_at.isoformat(),
            finished_at=finished.isoformat(),
            content_preview=(content or "")[:2000],
        )

        self.stages.append(entry)

        log_file = self.logs_dir / f"{stage}_{agent}.json"
        detail = {
            **entry.to_dict(),
            "content_full": content,
        }

        log_file.write_text(
            json.dumps(detail, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_manifest(
        self,
        *,
        requirement: str,
        extra: dict[str, Any] | None = None,
    ) -> Path:

        manifest = {
            "run_id": self.run_id,
            "requirement": requirement,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stages": [entry.to_dict() for entry in self.stages],
            "paths": {
                "tasks": str(self.run_root / "tasks.json"),
                "logs": str(self.logs_dir),
                "reports": str(self.reports_dir),
                "workspace": str(self.workspace_dir),
            },
        }

        if extra:

            manifest["extra"] = extra

        target = self.run_root / "run_manifest.json"
        target.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary = self._build_summary_markdown(requirement)
        self.save_report(
            "pipeline_summary",
            summary,
            filename="PIPELINE_SUMMARY.md",
        )

        return target

    def _build_summary_markdown(self, requirement: str) -> str:

        lines = [
            "# AI 软件团队流水线运行摘要",
            "",
            f"- **Run ID**: `{self.run_id}`",
            f"- **需求**: {requirement}",
            "",
            "## 阶段",
            "",
            "| 阶段 | Agent | 成功 | 模型 |",
            "|------|-------|------|------|",
        ]

        for entry in self.stages:

            ok = "是" if entry.success else "否"
            lines.append(
                f"| {entry.stage} | {entry.agent} | {ok} | {entry.model} |"
            )

        lines.extend(
            [
                "",
                "## 目录",
                "",
                f"- tasks: `{self.run_root / 'tasks.json'}`",
                f"- logs: `{self.logs_dir}`",
                f"- reports: `{self.reports_dir}`",
                f"- workspace: `{self.workspace_dir}`",
                "",
            ]
        )

        return "\n".join(lines)
