"""Task 5.8 full team pipeline tests."""

from __future__ import annotations

import json
from pathlib import Path

from applications.software_team.pipeline.team_pipeline import SoftwareTeamPipeline


def test_full_team_pipeline_creates_project_runs(tmp_path: Path) -> None:

    pipeline = SoftwareTeamPipeline(runs_base_dir=tmp_path)

    run_root = pipeline.run("开发一个用户管理系统", session_id="test-full")

    assert run_root.is_dir()
    assert (run_root / "tasks.json").is_file()
    assert (run_root / "logs").is_dir()
    assert (run_root / "reports").is_dir()
    assert (run_root / "workspace").is_dir()

    tasks = json.loads(
        (run_root / "tasks.json").read_text(encoding="utf-8")
    )

    assert tasks.get("requirement") == "开发一个用户管理系统"
    assert len(tasks.get("tasks", [])) >= 4

    reports = list((run_root / "reports").glob("*.md"))

    assert any(item.name == "PRD.md" for item in reports)
    assert any(item.name == "PIPELINE_SUMMARY.md" for item in reports)

    logs = list((run_root / "logs").glob("*.json"))

    assert len(logs) >= 7

    assert pipeline.last_project is not None
