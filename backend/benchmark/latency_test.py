"""Task 2.6 latency benchmark: TTFT, total time, tokens/s, GPU memory."""

from __future__ import annotations

import argparse
import sys
import urllib.error
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
if str(BENCHMARK_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_ROOT.parent))

from benchmark.common import BACKEND_OPENAI  # noqa: E402
from benchmark.common import BACKEND_QWEN  # noqa: E402
from benchmark.common import BACKEND_VLLM  # noqa: E402
from benchmark.common import DEFAULT_PROMPT  # noqa: E402
from benchmark.common import LatencyMetrics  # noqa: E402
from benchmark.common import Timer  # noqa: E402
from benchmark.common import ensure_results_dir  # noqa: E402
from benchmark.common import estimate_token_count  # noqa: E402
from benchmark.common import gpu_memory_snapshot  # noqa: E402
from benchmark.common import merge_gpu_snapshots  # noqa: E402
from benchmark.common import normalize_backend  # noqa: E402
from benchmark.common import now_iso  # noqa: E402
from benchmark.common import percentile  # noqa: E402
from benchmark.common import save_json  # noqa: E402
from benchmark.common import torch_gpu_memory_snapshot  # noqa: E402
from benchmark.http_client import resolve_model_from_api  # noqa: E402
from benchmark.http_client import resolve_openai_config  # noqa: E402
from benchmark.http_client import run_chat_stream_once  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 2.6 latency benchmark")
    parser.add_argument(
        "--backend",
        choices=("qwen", "vllm", "openai", "transformers", "local"),
        required=True,
    )
    parser.add_argument(
        "--openai-base-url",
        default=None,
        help="OpenAI-compatible API base (default: OPENAI_BASE_URL env)",
    )
    parser.add_argument(
        "--openai-api-key",
        default=None,
        help="API key (default: OPENAI_API_KEY env)",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output path (default: benchmark/results/latency_<backend>.json)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Synthetic metrics (no live backend); for report layout / CI",
    )
    return parser.parse_args()


def _resolve_vllm_model(base_url: str, model: str | None, timeout: int) -> str:
    if model:
        return model
    return resolve_model_from_api(base_url, timeout)


def _run_vllm_stream_once(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> tuple[float, float, int]:
    return run_chat_stream_once(
        base_url=base_url,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _run_openai_stream_once(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> tuple[float, float, int]:
    return run_chat_stream_once(
        base_url=base_url,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        timeout=timeout,
        api_key=api_key,
    )


def _run_transformers_once(
    *,
    prompt: str,
    max_tokens: int,
) -> tuple[float, float, int]:
    import torch
    from transformers import TextIteratorStreamer

    from app.llm.local.model_loader import ModelLoader
    from app.llm.local.tokenizer import build_qwen_prompt
    from app.llm.types import Message

    loader = ModelLoader.from_settings()
    loaded = loader.ensure_loaded()
    messages = [Message(role="user", content=prompt)]
    text_prompt = build_qwen_prompt(loaded.tokenizer, messages)
    inputs = loaded.tokenizer(text_prompt, return_tensors="pt")
    device = next(loaded.model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    streamer = TextIteratorStreamer(
        loaded.tokenizer,
        skip_special_tokens=True,
        skip_prompt=True,
    )
    gen_kwargs = {
        **inputs,
        "max_new_tokens": max_tokens,
        "do_sample": True,
        "temperature": 0.7,
        "streamer": streamer,
        "pad_token_id": loaded.tokenizer.eos_token_id,
    }

    import threading

    timer = Timer()
    ttft_ms: float | None = None
    parts: list[str] = []

    def _generate() -> None:
        with torch.inference_mode():
            loaded.model.generate(**gen_kwargs)

    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    for piece in streamer:
        if ttft_ms is None:
            ttft_ms = timer.elapsed_ms()
        parts.append(piece)
    thread.join(timeout=max_tokens * 2 + 60)

    total_ms = timer.elapsed_ms()
    answer = "".join(parts)
    tokens = estimate_token_count(answer)
    if ttft_ms is None:
        ttft_ms = total_ms
    return ttft_ms, total_ms, tokens


def _mock_latency(backend: str, args: argparse.Namespace) -> LatencyMetrics:
    gpu = merge_gpu_snapshots(gpu_memory_snapshot(), torch_gpu_memory_snapshot())
    profiles = {
        BACKEND_VLLM: (820.0, 1100.0, 4100.0, 5200.0, 28.5, "Qwen/Qwen2.5-0.5B-Instruct"),
        BACKEND_QWEN: (2400.0, 3200.0, 9800.0, 12000.0, 12.0, "Qwen/Qwen2.5-0.5B-Instruct"),
        BACKEND_OPENAI: (450.0, 680.0, 3200.0, 4100.0, 35.0, "gpt-4o-mini"),
    }
    ttft50, ttft95, total50, total95, tps, model = profiles.get(
        backend,
        profiles[BACKEND_QWEN],
    )
    return LatencyMetrics(
        backend=backend,
        model=args.model or model,
        runs=args.runs,
        ttft_ms_p50=ttft50,
        ttft_ms_p95=ttft95,
        total_ms_p50=total50,
        total_ms_p95=total95,
        tokens_per_sec_p50=tps,
        completion_tokens_avg=float(args.max_tokens) * 0.85,
        gpu_memory_mb=gpu,
        notes="mock data; run without --mock for measured results",
    )


def run_latency(args: argparse.Namespace) -> LatencyMetrics:
    backend = normalize_backend(args.backend)
    if args.mock:
        return _mock_latency(backend, args)

    ttft_samples: list[float] = []
    total_samples: list[float] = []
    tps_samples: list[float] = []
    token_counts: list[int] = []

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
        if not args.model:
            model = resolve_model_from_api(openai_url, args.timeout, openai_key or None)

    total_iters = args.warmup + args.runs
    for i in range(total_iters):
        if backend == BACKEND_VLLM:
            ttft, total, n_tokens = _run_vllm_stream_once(
                base_url=args.base_url,
                model=model,
                prompt=args.prompt,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        elif backend == BACKEND_OPENAI:
            ttft, total, n_tokens = _run_openai_stream_once(
                base_url=openai_url,
                api_key=openai_key,
                model=model,
                prompt=args.prompt,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
        else:
            ttft, total, n_tokens = _run_transformers_once(
                prompt=args.prompt,
                max_tokens=args.max_tokens,
            )

        if i < args.warmup:
            continue

        gen_sec = max((total - ttft) / 1000.0, 1e-6)
        tps = n_tokens / gen_sec

        ttft_samples.append(ttft)
        total_samples.append(total)
        tps_samples.append(tps)
        token_counts.append(n_tokens)

    gpu = merge_gpu_snapshots(gpu_memory_snapshot(), torch_gpu_memory_snapshot())

    return LatencyMetrics(
        backend=backend,
        model=model,
        runs=args.runs,
        ttft_ms_p50=percentile(ttft_samples, 50),
        ttft_ms_p95=percentile(ttft_samples, 95),
        total_ms_p50=percentile(total_samples, 50),
        total_ms_p95=percentile(total_samples, 95),
        tokens_per_sec_p50=percentile(tps_samples, 50),
        completion_tokens_avg=sum(token_counts) / max(len(token_counts), 1),
        gpu_memory_mb=gpu,
    )


def main() -> int:
    args = _parse_args()
    try:
        metrics = run_latency(args)
    except urllib.error.URLError as error:
        print(f"ERROR: cannot reach service ({error})")
        return 1
    except Exception as error:
        print(f"ERROR: {error}")
        return 1

    payload = {
        "task": "2.6",
        "kind": "latency",
        "timestamp": now_iso(),
        **metrics.__dict__,
    }
    out = args.output or (
        ensure_results_dir() / f"latency_{normalize_backend(args.backend)}.json"
    )
    save_json(out, payload)

    print("=" * 60)
    print("Task 2.6 Latency Benchmark")
    print("=" * 60)
    print(f"Backend   : {metrics.backend}")
    print(f"Model     : {metrics.model}")
    print(f"TTFT p50  : {metrics.ttft_ms_p50:.1f} ms")
    print(f"TTFT p95  : {metrics.ttft_ms_p95:.1f} ms")
    print(f"Total p50 : {metrics.total_ms_p50:.1f} ms")
    print(f"Total p95 : {metrics.total_ms_p95:.1f} ms")
    print(f"Tokens/s  : {metrics.tokens_per_sec_p50:.2f} (p50)")
    print(f"GPU MiB   : {metrics.gpu_memory_mb}")
    print(f"Saved     : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
