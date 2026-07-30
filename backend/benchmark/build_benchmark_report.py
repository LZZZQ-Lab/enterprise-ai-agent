"""Task 8.3: generate benchmark_report.md with cross-backend comparison."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
if str(BENCHMARK_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_ROOT.parent))

from benchmark.common import BENCHMARK_REPORT  # noqa: E402
from benchmark.common import RESULTS_DIR  # noqa: E402
from benchmark.common import SUITE_BACKENDS  # noqa: E402
from benchmark.common import backend_display_name  # noqa: E402
from benchmark.common import load_json  # noqa: E402
from benchmark.common import now_iso  # noqa: E402
from benchmark.common import normalize_backend  # noqa: E402


def _load_result(results_dir: Path, kind: str, backend: str) -> dict | None:
    path = results_dir / f"{kind}_{backend}.json"
    if not path.is_file():
        legacy = "transformers" if backend == "qwen" else backend
        path = results_dir / f"{kind}_{legacy}.json"
    if not path.is_file():
        return None
    return load_json(path)


def _memory_summary(gpu: dict) -> str:
    used = gpu.get("used_mib")
    total = gpu.get("total_mib")
    allocated = gpu.get("allocated_mib")
    if used is not None and total is not None:
        return f"{used:.0f} / {total:.0f} MiB (GPU)"
    if allocated is not None:
        return f"{allocated:.0f} MiB allocated (torch)"
    return "N/A"


def _best_backend(rows: list[tuple[str, float]], lower_is_better: bool = True) -> str:
    if not rows:
        return "-"
    key_fn = min if lower_is_better else max
    return key_fn(rows, key=lambda item: item[1])[0]


def build_benchmark_report(results_dir: Path) -> str:
    latency_rows: list[dict] = []
    throughput_rows: list[dict] = []

    for backend in SUITE_BACKENDS:
        lat = _load_result(results_dir, "latency", backend)
        thr = _load_result(results_dir, "throughput", backend)

        if lat:
            gpu = lat.get("gpu_memory_mb") or {}
            latency_rows.append(
                {
                    "backend": backend,
                    "label": backend_display_name(backend),
                    "model": lat.get("model", "-"),
                    "ttft_p50": lat["ttft_ms_p50"],
                    "ttft_p95": lat["ttft_ms_p95"],
                    "latency_p50": lat["total_ms_p50"],
                    "latency_p95": lat["total_ms_p95"],
                    "tokens_per_sec": lat["tokens_per_sec_p50"],
                    "memory": _memory_summary(gpu),
                    "notes": lat.get("notes") or "",
                }
            )
        if thr:
            gpu = thr.get("gpu_memory_mb") or {}
            throughput_rows.append(
                {
                    "backend": backend,
                    "label": backend_display_name(backend),
                    "model": thr.get("model", "-"),
                    "requests": thr["total_requests"],
                    "concurrency": thr["concurrent_requests"],
                    "wall_time_sec": thr["wall_time_sec"],
                    "throughput_req_s": thr["requests_per_sec"],
                    "throughput_tok_s": thr["tokens_per_sec"],
                    "memory": _memory_summary(gpu),
                    "notes": thr.get("notes") or "",
                }
            )

    ttft_best = _best_backend(
        [(r["label"], r["ttft_p50"]) for r in latency_rows],
        lower_is_better=True,
    )
    latency_best = _best_backend(
        [(r["label"], r["latency_p50"]) for r in latency_rows],
        lower_is_better=True,
    )
    tps_best = _best_backend(
        [(r["label"], r["tokens_per_sec"]) for r in latency_rows],
        lower_is_better=False,
    )
    thr_best = _best_backend(
        [(r["label"], r["throughput_tok_s"]) for r in throughput_rows],
        lower_is_better=False,
    )

    lines = [
        "# LLM Benchmark 性能对比报告（Task 8.3）",
        "",
        f"生成时间：{now_iso()}",
        "",
        "## 概述",
        "",
        "对比 **Qwen (Transformers)**、**vLLM**、**OpenAI** 三类推理后端的延迟与吞吐表现。",
        "",
        "| 指标 | 最优后端 |",
        "| --- | --- |",
        f"| TTFT (p50) | {ttft_best} |",
        f"| Latency / Total (p50) | {latency_best} |",
        f"| Token/s（单请求生成） | {tps_best} |",
        f"| Throughput Token/s（多请求） | {thr_best} |",
        "",
        "## 单请求（Latency）",
        "",
        "指标：TTFT、总延迟 (Latency)、生成 Token/s、Memory。",
        "",
        "| Backend | Model | TTFT p50 (ms) | TTFT p95 (ms) | Latency p50 (ms) | Latency p95 (ms) | Token/s (p50) | Memory |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in latency_rows:
        lines.append(
            f"| {row['label']} | {row['model']} | "
            f"{row['ttft_p50']:.1f} | {row['ttft_p95']:.1f} | "
            f"{row['latency_p50']:.1f} | {row['latency_p95']:.1f} | "
            f"{row['tokens_per_sec']:.2f} | {row['memory']} |"
        )

    if not latency_rows:
        lines.append("| (无数据) | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 多请求（Throughput）",
            "",
            "指标：并发请求数、Wall time、Requests/s、Token/s、Memory。",
            "",
            "| Backend | Model | Requests | Concurrency | Wall (s) | Req/s | Token/s | Memory |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in throughput_rows:
        lines.append(
            f"| {row['label']} | {row['model']} | "
            f"{row['requests']} | {row['concurrency']} | "
            f"{row['wall_time_sec']:.2f} | {row['throughput_req_s']:.3f} | "
            f"{row['throughput_tok_s']:.2f} | {row['memory']} |"
        )

    if not throughput_rows:
        lines.append("| (无数据) | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 运行方式",
            "",
            "```bash",
            "cd backend",
            "",
            "# Mock（CI / 无 GPU / 无 API Key）",
            "python -m benchmark.suite_runner --mock",
            "",
            "# Live：vLLM 需先 start_vllm_server.sh；OpenAI 需 OPENAI_API_KEY",
            "IP=$(hostname -I | awk '{print $1}')",
            "python -m benchmark.suite_runner \\",
            "  --backends qwen vllm openai \\",
            "  --base-url \"http://${IP}:8000/v1\"",
            "```",
            "",
            "结果 JSON：`benchmark/results/` · 报告：`artifacts/benchmark_report.md`",
            "",
        ]
    )

    mock_notes = {
        r["label"]
        for r in latency_rows + throughput_rows
        if "mock" in (r.get("notes") or "").lower()
    }
    if mock_notes:
        lines.extend(
            [
                "> **Note:** 部分结果为 `--mock` 合成数据，仅供布局与 CI 验证。",
                "",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate benchmark_report.md")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=BENCHMARK_REPORT)
    args = parser.parse_args()

    if not args.results_dir.is_dir():
        print(f"ERROR: results dir missing: {args.results_dir}")
        return 1

    report = build_benchmark_report(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
