"""Merge benchmark/results/*.json into docs/performance.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
if str(BENCHMARK_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_ROOT.parent))

from benchmark.common import DEFAULT_MODEL_LABEL  # noqa: E402
from benchmark.common import DOCS_PERFORMANCE  # noqa: E402
from benchmark.common import RESULTS_DIR  # noqa: E402
from benchmark.common import load_json  # noqa: E402
from benchmark.common import now_iso  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate docs/performance.md")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DOCS_PERFORMANCE,
    )
    return parser.parse_args()


def _section_latency(data: dict) -> list[str]:
    gpu = data.get("gpu_memory_mb") or {}
    used = gpu.get("used_mib")
    total = gpu.get("total_mib")
    mem_line = (
        f"GPU {used:.0f} / {total:.0f} MiB (nvidia-smi)"
        if used is not None and total is not None
        else str(gpu)
    )
    note = data.get("notes") or ""
    lines = [
        "**Latency:**",
        f"- TTFT p50 / p95: {data['ttft_ms_p50']:.1f} ms / {data['ttft_ms_p95']:.1f} ms",
        f"- Total p50 / p95: {data['total_ms_p50']:.1f} ms / {data['total_ms_p95']:.1f} ms",
        f"- Generation tokens/s (p50): {data['tokens_per_sec_p50']:.2f}",
        f"- Avg completion tokens: {data['completion_tokens_avg']:.1f} ({data['runs']} runs)",
        f"- Memory: {mem_line}",
    ]
    if note:
        lines.append(f"- Note: {note}")
    lines.append("")
    return lines


def _section_throughput(data: dict) -> list[str]:
    gpu = data.get("gpu_memory_mb") or {}
    return [
        "**Throughput:**",
        f"- {data['total_requests']} requests, concurrency {data['concurrent_requests']}",
        f"- Wall time: {data['wall_time_sec']:.2f} s",
        f"- Requests/s: {data['requests_per_sec']:.3f}",
        f"- Tokens/s: {data['tokens_per_sec']:.2f}",
        f"- Total completion tokens: {data['total_completion_tokens']}",
        f"- Memory: {gpu}",
        *( [f"- Note: {data['notes']}"] if data.get("notes") else [] ),
        "",
    ]


def _backend_block(
    label: str,
    latency: dict | None,
    throughput: dict | None,
) -> list[str]:
    lines = [
        f"### 推理方式：{label}",
        "",
        f"模型：{DEFAULT_MODEL_LABEL}",
        "",
    ]
    if latency:
        lines.extend(_section_latency(latency))
    else:
        lines.extend(["**Latency:**", "- (未运行 `latency_test.py`)", ""])
    if throughput:
        lines.extend(_section_throughput(throughput))
    else:
        lines.extend(["**Throughput:**", "- (未运行 `throughput_test.py`)", ""])
    return lines


def build_markdown(results_dir: Path) -> str:
    lat_vllm = results_dir / "latency_vllm.json"
    lat_qwen = results_dir / "latency_qwen.json"
    lat_tr = results_dir / "latency_transformers.json"
    thr_vllm = results_dir / "throughput_vllm.json"
    thr_qwen = results_dir / "throughput_qwen.json"
    thr_tr = results_dir / "throughput_transformers.json"

    lines = [
        "# 模型推理性能报告（Task 2.6）",
        "",
        f"生成时间：{now_iso()}",
        "",
        "硬件参考：NVIDIA GeForce RTX 2050 4GB · WSL2 · Qwen2.5-0.5B-Instruct",
        "",
        "运行基准：",
        "",
        "```bash",
        "cd backend",
        "# vLLM 需先 start_vllm_server.sh；WSL mirrored 网络请用网卡 IP",
        "IP=$(hostname -I | awk '{print $1}')",
        "python -m benchmark.latency_test --backend vllm --base-url \"http://${IP}:8000/v1\"",
        "python -m benchmark.throughput_test --backend vllm --base-url \"http://${IP}:8000/v1\"",
        "python -m benchmark.latency_test --backend transformers",
        "python -m benchmark.throughput_test --backend transformers",
        "python -m benchmark.generate_report",
        "```",
        "",
        "---",
        "",
    ]

    lines.extend(
        _backend_block(
            "vLLM",
            load_json(lat_vllm) if lat_vllm.is_file() else None,
            load_json(thr_vllm) if thr_vllm.is_file() else None,
        )
    )
    lines.append("---")
    lines.append("")
    lines.extend(
        _backend_block(
            "Transformers",
            load_json(lat_qwen)
            if lat_qwen.is_file()
            else (load_json(lat_tr) if lat_tr.is_file() else None),
            load_json(thr_qwen)
            if thr_qwen.is_file()
            else (load_json(thr_tr) if thr_tr.is_file() else None),
        )
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    if not args.results_dir.is_dir():
        print(f"ERROR: results dir missing: {args.results_dir}")
        return 1
    md = build_markdown(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
