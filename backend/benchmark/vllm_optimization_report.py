"""Task 4.4: 合并 baseline / optimized vLLM 压测结果，输出对比报告。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BENCHMARK_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = BENCHMARK_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmark.common import RESULTS_DIR  # noqa: E402
from benchmark.common import load_json  # noqa: E402
from benchmark.common import now_iso  # noqa: E402


def _level_by_concurrency(
    payload: dict[str, Any],
) -> dict[int, dict[str, Any]]:

    levels = payload.get("levels") or []

    return {
        int(item["concurrency"]): item
        for item in levels
    }


def _latency_improvement(before: float, after: float) -> str:

    if before <= 0:

        return "N/A"

    delta = (before - after) / before * 100.0

    return f"{delta:+.1f}%"


def _throughput_improvement(before: float, after: float) -> str:

    if before <= 0:

        return "N/A"

    delta = (after - before) / before * 100.0

    return f"{delta:+.1f}%"


def build_comparison_markdown(
    baseline: dict[str, Any],
    optimized: dict[str, Any],
) -> str:

    base_levels = _level_by_concurrency(baseline)
    opt_levels = _level_by_concurrency(optimized)

    lines = [
        "# vLLM 推理优化对比报告（Task 4.4）",
        "",
        f"生成时间：{now_iso()}",
        "",
        "## 服务配置",
        "",
        "### Baseline",
        "",
        "```json",
        json.dumps(
            baseline.get("server_profile") or {},
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "### Optimized",
        "",
        "```json",
        json.dumps(
            optimized.get("server_profile") or {},
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "调优维度：**max_model_len**、**gpu_memory_utilization**、"
        "**max_num_seqs（batch）**、**max_num_batched_tokens**、"
        "**enable_prefix_caching（KV）**、**enforce_eager**。",
        "",
        "## 并发压测对比",
        "",
        "| 并发 | 指标 | Baseline | Optimized | 变化 |",
        "|------|------|----------|-----------|------|",
    ]

    for concurrency in sorted(set(base_levels) | set(opt_levels)):

        base = base_levels.get(concurrency)
        opt = opt_levels.get(concurrency)

        if not base or not opt:

            continue

        pairs = [
            ("TTFT p50 (ms)", "ttft_ms_p50", "latency"),
            ("TTFT p95 (ms)", "ttft_ms_p95", "latency"),
            ("Latency p50 (ms)", "latency_ms_p50", "latency"),
            ("Latency p95 (ms)", "latency_ms_p95", "latency"),
            ("Throughput req/s", "requests_per_sec", "throughput"),
            ("Throughput tok/s", "tokens_per_sec", "throughput"),
        ]

        for label, key, kind in pairs:

            before = float(base[key])
            after = float(opt[key])

            if kind == "throughput":

                change = _throughput_improvement(before, after)

            else:

                change = _latency_improvement(before, after)

            lines.append(
                f"| {concurrency} | {label} | {before:.2f} | "
                f"{after:.2f} | {change} |"
            )

    lines.extend(
        [
            "",
            "## 解读",
            "",
            "- **Latency / TTFT 变化**：正百分比表示 optimized 延迟更低。",
            "- **Throughput 变化**：正百分比表示 optimized 吞吐更高。",
            "- 并发 **50** 时 batch 与 KV cache 调优通常最明显。",
            "",
            "## 复现",
            "",
            "```bash",
            "cd backend",
            "VLLM_PROFILE=baseline bash scripts/start_vllm_server.sh",
            "python -m benchmark.vllm_concurrency_benchmark --profile baseline",
            "# 重启服务",
            "VLLM_PROFILE=optimized bash scripts/start_vllm_server.sh",
            "python -m benchmark.vllm_concurrency_benchmark --profile optimized",
            "python -m benchmark.vllm_optimization_report",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Generate vLLM optimization comparison report",
    )

    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
    )

    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--optimized",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "vllm_performance.md",
    )

    parser.add_argument(
        "--artifacts",
        type=Path,
        default=BACKEND_ROOT
        / "artifacts"
        / "optimization"
        / "vllm",
    )

    return parser.parse_args()


def main() -> int:

    args = _parse_args()

    baseline_path = args.baseline or (
        args.results_dir / "vllm_concurrency_baseline.json"
    )

    optimized_path = args.optimized or (
        args.results_dir / "vllm_concurrency_optimized.json"
    )

    if not baseline_path.is_file() or not optimized_path.is_file():

        print(
            "ERROR: need both baseline and optimized JSON. "
            f"Missing: baseline={baseline_path.is_file()} "
            f"optimized={optimized_path.is_file()}"
        )
        print(
            "Hint: run vllm_concurrency_benchmark --mock for both profiles"
        )
        return 1

    baseline = load_json(baseline_path)
    optimized = load_json(optimized_path)

    markdown = build_comparison_markdown(baseline, optimized)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.artifacts.mkdir(parents=True, exist_ok=True)

    (args.artifacts / "vllm_performance.md").write_text(
        markdown,
        encoding="utf-8",
    )

    print(f"Wrote {args.output}")
    print(f"Wrote {args.artifacts / 'vllm_performance.md'}")
    return 0


if __name__ == "__main__":

    raise SystemExit(main())
