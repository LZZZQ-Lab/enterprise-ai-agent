"""Task 8.3: unified LLM benchmark suite (single + multi request)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmark.build_benchmark_report import build_benchmark_report
from benchmark.common import BENCHMARK_REPORT
from benchmark.common import RESULTS_DIR
from benchmark.common import SUITE_BACKENDS
from benchmark.common import normalize_backend
from benchmark.common import now_iso
from benchmark.common import save_json
from benchmark.latency_test import run_latency
from benchmark.throughput_test import run_throughput


@dataclass
class SuiteResult:
    backend: str
    single: dict[str, Any]
    multi: dict[str, Any]


def _latency_args(
    base: argparse.Namespace,
    backend: str,
) -> argparse.Namespace:
    results_dir = base.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    return argparse.Namespace(
        backend=backend,
        base_url=base.base_url,
        openai_base_url=base.openai_base_url,
        openai_api_key=base.openai_api_key,
        model=base.model,
        prompt=base.prompt,
        max_tokens=base.max_tokens,
        runs=base.runs,
        warmup=base.warmup,
        timeout=base.timeout,
        output=results_dir / f"latency_{backend}.json",
        mock=base.mock,
    )


def _throughput_args(
    base: argparse.Namespace,
    backend: str,
) -> argparse.Namespace:
    results_dir = base.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    return argparse.Namespace(
        backend=backend,
        base_url=base.base_url,
        openai_base_url=base.openai_base_url,
        openai_api_key=base.openai_api_key,
        model=base.model,
        prompt=base.prompt,
        max_tokens=base.throughput_max_tokens,
        requests=base.requests,
        concurrency=base.concurrency,
        timeout=base.timeout,
        output=results_dir / f"throughput_{backend}.json",
        mock=base.mock,
    )


def run_suite(args: argparse.Namespace) -> list[SuiteResult]:
    backends = [normalize_backend(b) for b in args.backends]
    results: list[SuiteResult] = []

    for backend in backends:
        lat = run_latency(_latency_args(args, backend))
        lat_payload = {
            "task": "8.3",
            "kind": "single_request",
            "mode": "latency",
            "timestamp": now_iso(),
            **asdict(lat),
        }
        save_json(_latency_args(args, backend).output, lat_payload)

        thr = run_throughput(_throughput_args(args, backend))
        thr_payload = {
            "task": "8.3",
            "kind": "multi_request",
            "mode": "throughput",
            "timestamp": now_iso(),
            **asdict(thr),
        }
        save_json(_throughput_args(args, backend).output, thr_payload)

        results.append(
            SuiteResult(
                backend=backend,
                single=lat_payload,
                multi=thr_payload,
            )
        )

    return results


def write_suite_manifest(results: list[SuiteResult], path: Path) -> None:
    payload = {
        "task": "8.3",
        "timestamp": now_iso(),
        "backends": [r.backend for r in results],
        "results": [
            {"backend": r.backend, "single": r.single, "multi": r.multi}
            for r in results
        ],
    }
    save_json(path, payload)


def parse_suite_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 8.3 LLM benchmark suite")
    parser.add_argument(
        "--backends",
        nargs="+",
        default=list(SUITE_BACKENDS),
        choices=("qwen", "vllm", "openai", "transformers", "local"),
        help="Backends to benchmark (default: qwen vllm openai)",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--prompt",
        default="请用三句话介绍企业级 AI 助手平台可以做什么。",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--throughput-max-tokens", type=int, default=64)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BENCHMARK_REPORT,
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Synthetic metrics for all backends (CI / layout validation)",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Only run benchmarks, do not write benchmark_report.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_suite_args(argv)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = run_suite(args)
    except Exception as error:
        print(f"ERROR: {error}")
        return 1

    manifest = args.results_dir / "suite_manifest.json"
    write_suite_manifest(results, manifest)

    if not args.skip_report:
        report = build_benchmark_report(args.results_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"Report: {args.report}")

    print(f"Manifest: {manifest}")
    print(f"Backends: {', '.join(r.backend for r in results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
