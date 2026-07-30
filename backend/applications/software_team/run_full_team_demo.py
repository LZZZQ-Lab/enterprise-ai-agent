#!/usr/bin/env python3
"""
Task 5.8：AI 软件团队完整 Demo。

用法：
    cd backend
    python -m applications.software_team.run_full_team_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_REQUIREMENT = "开发一个用户管理系统"


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Full AI Software Team Demo (Task 5.8)",
    )

    parser.add_argument(
        "--requirement",
        default=DEFAULT_REQUIREMENT,
    )

    parser.add_argument(
        "--runs-dir",
        default=str(BACKEND_ROOT / "project_runs"),
    )

    args = parser.parse_args()

    from applications.software_team.pipeline.team_pipeline import (
        SoftwareTeamPipeline,
    )

    pipeline = SoftwareTeamPipeline(
        runs_base_dir=Path(args.runs_dir),
    )

    run_root = pipeline.run(args.requirement)

    print(f"Run completed: {run_root}")
    print(f"  tasks.json : {run_root / 'tasks.json'}")
    print(f"  logs/      : {run_root / 'logs'}")
    print(f"  reports/   : {run_root / 'reports'}")
    print(f"  workspace/ : {run_root / 'workspace'}")
    print("")
    print(
        (run_root / "reports" / "PIPELINE_SUMMARY.md").read_text(
            encoding="utf-8"
        )
    )


if __name__ == "__main__":

    main()
