"""Task 2.6 throughput benchmark: concurrent requests, aggregate tokens/s."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
if str(BENCHMARK_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_ROOT.parent))

from benchmark.common import BACKEND_OPENAI  # noqa: E402
from benchmark.common import BACKEND_QWEN  # noqa: E402
from benchmark.common import BACKEND_VLLM  # noqa: E402
from benchmark.common import DEFAULT_PROMPT  # noqa: E402
from benchmark.common import ThroughputMetrics  # noqa: E402
from benchmark.common import ensure_results_dir  # noqa: E402
from benchmark.common import gpu_memory_snapshot  # noqa: E402
from benchmark.common import merge_gpu_snapshots  # noqa: E402
from benchmark.common import normalize_backend  # noqa: E402
from benchmark.common import now_iso  # noqa: E402
from benchmark.common import save_json  # noqa: E402
from benchmark.common import torch_gpu_memory_snapshot  # noqa: E402
from benchmark.http_client import resolve_openai_config  # noqa: E402
from benchmark.latency_test import _resolve_vllm_model  # noqa: E402
from benchmark.latency_test import _run_openai_stream_once  # noqa: E402
from benchmark.latency_test import _run_transformers_once  # noqa: E402
from benchmark.latency_test import _run_vllm_stream_once  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 2.6 throughput benchmark")
    parser.add_argument(
        "--backend",
        choices=("qwen", "vllm", "openai", "transformers", "local"),
        required=True,
    )
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Synthetic metrics (no live backend)",
    )
    return parser.parse_args()


def _one_vllm_job(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> int:
    _ttft, _total, n_tokens = _run_vllm_stream_once(
        base_url=base_url,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return n_tokens


def _one_transformers_job(*, prompt: str, max_tokens: int) -> int:
    _ttft, _total, n_tokens = _run_transformers_once(
        prompt=prompt,
        max_tokens=max_tokens,
    )
    return n_tokens


def _one_openai_job(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> int:
    _ttft, _total, n_tokens = _run_openai_stream_once(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return n_tokens


def _mock_throughput(backend: str, args: argparse.Namespace) -> ThroughputMetrics:
    gpu = merge_gpu_snapshots(
        gpu_memory_snapshot(),
        torch_gpu_memory_snapshot(),
    )
    profiles = {
        BACKEND_VLLM: (48.0, "Qwen/Qwen2.5-0.5B-Instruct"),
        BACKEND_QWEN: (96.0, "Qwen/Qwen2.5-0.5B-Instruct"),
        BACKEND_OPENAI: (38.0, "gpt-4o-mini"),
    }
    wall, model = profiles.get(backend, profiles[BACKEND_QWEN])
    total_tok = args.requests * int(args.max_tokens * 0.8)
    return ThroughputMetrics(
        backend=backend,
        model=args.model or model,
        concurrent_requests=max(1, min(args.concurrency, args.requests)),
        total_requests=args.requests,
        wall_time_sec=wall,
        total_completion_tokens=total_tok,
        requests_per_sec=args.requests / wall,
        tokens_per_sec=total_tok / wall,
        gpu_memory_mb=gpu,
        notes="mock data; run without --mock for measured results",
    )


def run_throughput(args: argparse.Namespace) -> ThroughputMetrics:
    backend = normalize_backend(args.backend)
    if args.mock:
        return _mock_throughput(backend, args)

    model = args.model or "Qwen/Qwen2.5-0.5B-Instruct"
    openai_url = ""
    openai_key = ""
    if backend == BACKEND_VLLM:
        model = _resolve_vllm_model(args.base_url, args.model, args.timeout)
    elif backend == BACKEND_OPENAI:
        openai_url, openai_key, default_model = resolve_openai_config(
            base_url=args.openai_base_url,
            api_key=args.openai_api_key,
            model=args.model,
        )
        model = args.model or default_model

    def _job(_index: int) -> int:
        if backend == BACKEND_VLLM:
            return _one_vllm_job(
                base_url=args.base_url,
                model=model,
                prompt=args.prompt,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        if backend == BACKEND_OPENAI:
            return _one_openai_job(
                base_url=openai_url,
                api_key=openai_key,
                model=model,
                prompt=args.prompt,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        return _one_transformers_job(
            prompt=args.prompt,
            max_tokens=args.max_tokens,
        )

    gpu_before = merge_gpu_snapshots(
        gpu_memory_snapshot(),
        torch_gpu_memory_snapshot(),
    )
    start = time.perf_counter()
    total_tokens = 0
    workers = max(1, min(args.concurrency, args.requests))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_job, i) for i in range(args.requests)]
        for future in as_completed(futures):
            total_tokens += future.result()

    wall = time.perf_counter() - start
    gpu_after = merge_gpu_snapshots(
        gpu_memory_snapshot(),
        torch_gpu_memory_snapshot(),
    )

    return ThroughputMetrics(
        backend=backend,
        model=model,
        concurrent_requests=workers,
        total_requests=args.requests,
        wall_time_sec=wall,
        total_completion_tokens=total_tokens,
        requests_per_sec=args.requests / max(wall, 1e-6),
        tokens_per_sec=total_tokens / max(wall, 1e-6),
        gpu_memory_mb={
            **gpu_before,
            "used_mib_after": gpu_after.get("used_mib"),
            "allocated_mib_after": gpu_after.get("allocated_mib"),
        },
    )


def main() -> int:
    args = _parse_args()
    try:
        metrics = run_throughput(args)
    except urllib.error.URLError as error:
        print(f"ERROR: cannot reach service ({error})")
        return 1
    except Exception as error:
        print(f"ERROR: {error}")
        return 1

    payload = {
        "task": "2.6",
        "kind": "throughput",
        "timestamp": now_iso(),
        **metrics.__dict__,
    }
    out = args.output or (
        ensure_results_dir() / f"throughput_{normalize_backend(args.backend)}.json"
    )
    save_json(out, payload)

    print("=" * 60)
    print("Task 2.6 Throughput Benchmark")
    print("=" * 60)
    print(f"Backend     : {metrics.backend}")
    print(f"Model       : {metrics.model}")
    print(
        f"Requests    : {metrics.total_requests} "
        f"@ concurrency {metrics.concurrent_requests}"
    )
    print(f"Wall time   : {metrics.wall_time_sec:.2f} s")
    print(f"Req/s       : {metrics.requests_per_sec:.3f}")
    print(f"Tokens/s    : {metrics.tokens_per_sec:.2f}")
    print(f"GPU MiB     : {metrics.gpu_memory_mb}")
    print(f"Saved       : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
