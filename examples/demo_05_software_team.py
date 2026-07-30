#!/usr/bin/env python3
"""
Demo 05 — AI 软件团队

Manager → Product → Architecture → Developer → Reviewer → Tester → DevOps

Mock 模式使用内置 Demo LLM + Tool Bootstrap，无需 API Key / GPU。
产物写入 examples/_output/software_team/{run_id}/

用法:
    python examples/demo_05_software_team.py
    python examples/demo_05_software_team.py --requirement "开发博客系统"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import OUTPUT_ROOT, bootstrap


def main() -> None:
    bootstrap()

    parser = argparse.ArgumentParser(description="Demo 05 — AI Software Team")
    parser.add_argument(
        "--requirement",
        default="开发一个用户管理系统",
        help="用户需求描述",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_ROOT / "software_team"),
        help="运行记录根目录",
    )
    args = parser.parse_args()

    print("=== Demo 05: AI Software Team [Mock] ===\n")
    print(f"Requirement: {args.requirement}\n")

    from app.config import AgentConfig
    from applications.software_team.pipeline.team_pipeline import (
        SoftwareTeamPipeline,
    )

    config = AgentConfig(
        max_iterations=6,
        enable_mcp=False,
        enable_rag=False,
        enable_trace=False,
    )

    pipeline = SoftwareTeamPipeline(
        runs_base_dir=Path(args.output_dir),
        config=config,
    )

    run_root = pipeline.run(args.requirement)

    summary_path = run_root / "reports" / "PIPELINE_SUMMARY.md"
    print(f"Run root : {run_root}")
    print(f"  tasks  : {run_root / 'tasks.json'}")
    print(f"  reports: {run_root / 'reports'}")
    print(f"  workspace: {run_root / 'workspace'}")
    print()

    if summary_path.is_file():
        print("--- PIPELINE_SUMMARY (excerpt) ---")
        text = summary_path.read_text(encoding="utf-8")
        lines = text.splitlines()[:24]
        print("\n".join(lines))
        if len(text.splitlines()) > 24:
            print("  ...")
    else:
        print("(No PIPELINE_SUMMARY.md — check reports/ directory)")

    print("\nDone.")


if __name__ == "__main__":
    main()
