#!/usr/bin/env python3
"""
Task 4.4：vLLM 优化前后压测一键脚本（mock 或连 live vLLM）。

用法:
    cd backend
    python -m scripts.vllm_perf_benchmark --mock
    python -m scripts.vllm_perf_benchmark --base-url http://HOST:8000/v1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:

    parser = argparse.ArgumentParser(
        description="Run baseline + optimized vLLM concurrency benchmarks",
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/v1",
    )

    parser.add_argument("--mock", action="store_true")
    parser.add_argument(
        "--concurrency",
        default="1,10,50",
    )

    args = parser.parse_args()

    mock_flag = ["--mock"] if args.mock else []

    for profile in ("baseline", "optimized"):

        cmd = [
            sys.executable,
            "-m",
            "benchmark.vllm_concurrency_benchmark",
            "--profile",
            profile,
            "--base-url",
            args.base_url,
            "--concurrency",
            args.concurrency,
            *mock_flag,
        ]

        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, cwd=BACKEND_ROOT)

        if result.returncode != 0:

            return result.returncode

    report_cmd = [
        sys.executable,
        "-m",
        "benchmark.vllm_optimization_report",
    ]

    print("Running:", " ".join(report_cmd))
    return subprocess.run(report_cmd, cwd=BACKEND_ROOT).returncode


if __name__ == "__main__":

    raise SystemExit(main())
