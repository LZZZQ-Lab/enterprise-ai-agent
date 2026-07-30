"""Task 4.4: vLLM 并发压测（TTFT / Latency / Throughput）。"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
if str(BENCHMARK_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_ROOT.parent))

from benchmark.common import DEFAULT_PROMPT  # noqa: E402
from benchmark.common import ensure_results_dir  # noqa: E402
from benchmark.common import gpu_memory_snapshot  # noqa: E402
from benchmark.common import merge_gpu_snapshots  # noqa: E402
from benchmark.common import now_iso  # noqa: E402
from benchmark.common import percentile  # noqa: E402
from benchmark.common import save_json  # noqa: E402
from benchmark.common import torch_gpu_memory_snapshot  # noqa: E402
from benchmark.latency_test import _resolve_vllm_model  # noqa: E402
from benchmark.latency_test import _run_vllm_stream_once  # noqa: E402


DEFAULT_CONCURRENCY_LEVELS = (1, 10, 50)


@dataclass
class RequestSample:
    ttft_ms: float
    total_ms: float
    completion_tokens: int


@dataclass
class ConcurrencyLevelMetrics:
    profile: str
    concurrency: int
    total_requests: int
    wall_time_sec: float
    ttft_ms_p50: float
    ttft_ms_p95: float
    latency_ms_p50: float
    latency_ms_p95: float
    requests_per_sec: float
    tokens_per_sec: float
    completion_tokens_total: int
    gpu_memory_mb: dict[str, float | None]
    notes: str = ""


@dataclass
class VllmConcurrencyReport:
    profile: str
    model: str
    base_url: str
    max_tokens: int
    prompt: str
    levels: list[ConcurrencyLevelMetrics]
    server_profile: dict | None
    created_at: str

    def to_dict(self) -> dict:

        return {
            "task": "4.4",
            "kind": "vllm_concurrency",
            "profile": self.profile,
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "prompt": self.prompt,
            "created_at": self.created_at,
            "server_profile": self.server_profile,
            "levels": [asdict(level) for level in self.levels],
        }


def _requests_for_concurrency(concurrency: int) -> int:

    if concurrency <= 1:

        return 10

    return max(concurrency, 10)


def _run_one(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> RequestSample:

    ttft, total, tokens = _run_vllm_stream_once(
        base_url=base_url,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    return RequestSample(
        ttft_ms=ttft,
        total_ms=total,
        completion_tokens=tokens,
    )


def run_level(
    *,
    profile_label: str,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    concurrency: int,
    timeout: int,
) -> ConcurrencyLevelMetrics:

    total_requests = _requests_for_concurrency(concurrency)
    workers = max(1, min(concurrency, total_requests))

    gpu_before = merge_gpu_snapshots(
        gpu_memory_snapshot(),
        torch_gpu_memory_snapshot(),
    )

    samples: list[RequestSample] = []

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:

        futures = [
            pool.submit(
                _run_one,
                base_url=base_url,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            for _ in range(total_requests)
        ]

        for future in as_completed(futures):

            samples.append(future.result())

    wall = time.perf_counter() - start

    gpu_after = merge_gpu_snapshots(
        gpu_memory_snapshot(),
        torch_gpu_memory_snapshot(),
    )

    ttft_vals = [sample.ttft_ms for sample in samples]
    lat_vals = [sample.total_ms for sample in samples]
    total_tokens = sum(
        sample.completion_tokens for sample in samples
    )

    return ConcurrencyLevelMetrics(
        profile=profile_label,
        concurrency=workers,
        total_requests=total_requests,
        wall_time_sec=wall,
        ttft_ms_p50=percentile(ttft_vals, 50),
        ttft_ms_p95=percentile(ttft_vals, 95),
        latency_ms_p50=percentile(lat_vals, 50),
        latency_ms_p95=percentile(lat_vals, 95),
        requests_per_sec=total_requests / max(wall, 1e-6),
        tokens_per_sec=total_tokens / max(wall, 1e-6),
        completion_tokens_total=total_tokens,
        gpu_memory_mb={
            **gpu_before,
            "used_mib_after": gpu_after.get("used_mib"),
        },
    )


def run_mock_report(
    *,
    profile_label: str,
    model: str,
    base_url: str,
    max_tokens: int,
    prompt: str,
    levels: tuple[int, ...],
    server_profile: dict | None,
) -> VllmConcurrencyReport:

    baseline_factor = 1.0 if profile_label == "baseline" else 0.88

    metrics: list[ConcurrencyLevelMetrics] = []

    for concurrency in levels:

        scale = 1.0 + (concurrency - 1) * 0.012

        if profile_label == "optimized":

            scale *= 0.92

        ttft_p50 = 72.0 * baseline_factor * scale
        ttft_p95 = 85.0 * baseline_factor * scale
        lat_p50 = 2800.0 * baseline_factor * scale
        lat_p95 = 3400.0 * baseline_factor * scale
        reqs = _requests_for_concurrency(concurrency)
        wall = (reqs / max(concurrency, 1)) * lat_p50 / 1000.0

        if profile_label == "optimized":

            wall *= 0.82

        total_tokens = int(reqs * max_tokens * 0.82)

        metrics.append(
            ConcurrencyLevelMetrics(
                profile=profile_label,
                concurrency=concurrency,
                total_requests=reqs,
                wall_time_sec=wall,
                ttft_ms_p50=ttft_p50,
                ttft_ms_p95=ttft_p95,
                latency_ms_p50=lat_p50,
                latency_ms_p95=lat_p95,
                requests_per_sec=reqs / max(wall, 1e-6),
                tokens_per_sec=total_tokens / max(wall, 1e-6),
                completion_tokens_total=total_tokens,
                gpu_memory_mb={
                    "used_mib": 2855.0,
                    "total_mib": 4096.0,
                },
                notes="mock data; run without --mock for measured results",
            )
        )

    return VllmConcurrencyReport(
        profile=profile_label,
        model=model,
        base_url=base_url,
        max_tokens=max_tokens,
        prompt=prompt,
        levels=metrics,
        server_profile=server_profile,
        created_at=now_iso(),
    )


def run_vllm_concurrency_benchmark(
    *,
    profile_label: str,
    base_url: str,
    model: str | None,
    prompt: str,
    max_tokens: int,
    concurrency_levels: tuple[int, ...],
    timeout: int,
    server_profile: dict | None = None,
    mock: bool = False,
) -> VllmConcurrencyReport:

    resolved_model = model or "Qwen/Qwen2.5-0.5B-Instruct"

    if mock:

        return run_mock_report(
            profile_label=profile_label,
            model=resolved_model,
            base_url=base_url,
            max_tokens=max_tokens,
            prompt=prompt,
            levels=concurrency_levels,
            server_profile=server_profile,
        )

    resolved_model = _resolve_vllm_model(
        base_url,
        model,
        timeout,
    )

    level_metrics: list[ConcurrencyLevelMetrics] = []

    for concurrency in concurrency_levels:

        level_metrics.append(
            run_level(
                profile_label=profile_label,
                base_url=base_url,
                model=resolved_model,
                prompt=prompt,
                max_tokens=max_tokens,
                concurrency=concurrency,
                timeout=timeout,
            )
        )

    return VllmConcurrencyReport(
        profile=profile_label,
        model=resolved_model,
        base_url=base_url,
        max_tokens=max_tokens,
        prompt=prompt,
        levels=level_metrics,
        server_profile=server_profile,
        created_at=now_iso(),
    )


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Task 4.4 vLLM concurrency benchmark",
    )

    parser.add_argument(
        "--profile",
        default="baseline",
        help="Label for current server tuning (baseline|optimized)",
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/v1",
    )

    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument(
        "--concurrency",
        default="1,10,50",
        help="Comma-separated concurrency levels",
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--mock", action="store_true")

    return parser.parse_args()


def main() -> int:

    args = _parse_args()

    levels_tuple = tuple(
        int(part.strip())
        for part in args.concurrency.split(",")
        if part.strip()
    )

    server_profile = None

    try:

        from app.optimization.vllm_tuning import get_profile

        server_profile = get_profile(args.profile).to_dict()

    except (ImportError, KeyError, OSError):

        server_profile = None

    try:

        report = run_vllm_concurrency_benchmark(
            profile_label=args.profile,
            base_url=args.base_url,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            concurrency_levels=levels_tuple or DEFAULT_CONCURRENCY_LEVELS,
            timeout=args.timeout,
            server_profile=server_profile,
            mock=args.mock,
        )

    except urllib.error.URLError as error:

        print(f"ERROR: cannot reach vLLM ({error})")
        return 1

    except Exception as error:

        print(f"ERROR: {error}")
        return 1

    out = args.output or (
        ensure_results_dir()
        / f"vllm_concurrency_{args.profile}.json"
    )

    save_json(out, report.to_dict())

    print("=" * 60)
    print("Task 4.4 vLLM Concurrency Benchmark")
    print("=" * 60)
    print(f"Profile : {report.profile}")
    print(f"Model   : {report.model}")

    for level in report.levels:

        print(
            f"  c={level.concurrency:>2} "
            f"TTFT p50={level.ttft_ms_p50:.1f}ms "
            f"Lat p50={level.latency_ms_p50:.1f}ms "
            f"req/s={level.requests_per_sec:.2f} "
            f"tok/s={level.tokens_per_sec:.1f}"
        )

    print(f"Saved   : {out}")
    return 0


if __name__ == "__main__":

    raise SystemExit(main())
