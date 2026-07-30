"""Task 4.4 vLLM tuning and benchmark report tests."""

from __future__ import annotations

from app.optimization.vllm_tuning import get_profile
from app.optimization.vllm_tuning import load_profiles
from benchmark.vllm_concurrency_benchmark import run_mock_report
from benchmark.vllm_optimization_report import build_comparison_markdown

def test_load_vllm_profiles() -> None:

    profiles = load_profiles()

    assert "baseline" in profiles
    assert "optimized" in profiles
    assert (
        profiles["optimized"].gpu_memory_utilization
        > profiles["baseline"].gpu_memory_utilization
    )


def test_optimized_has_prefix_caching() -> None:

    optimized = get_profile("optimized")

    assert optimized.enable_prefix_caching is True
    assert optimized.max_num_seqs >= get_profile("baseline").max_num_seqs


def test_serve_argv_includes_batch_and_kv() -> None:

    optimized = get_profile("optimized")
    argv = optimized.serve_argv()

    assert "--max-num-seqs" in argv
    assert "--enable-prefix-caching" in argv
    assert "--enforce-eager" not in argv


def test_mock_comparison_markdown() -> None:

    baseline = run_mock_report(
        profile_label="baseline",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        base_url="http://127.0.0.1:8000/v1",
        max_tokens=128,
        prompt="hi",
        levels=(1, 10, 50),
        server_profile=get_profile("baseline").to_dict(),
    ).to_dict()

    optimized = run_mock_report(
        profile_label="optimized",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        base_url="http://127.0.0.1:8000/v1",
        max_tokens=128,
        prompt="hi",
        levels=(1, 10, 50),
        server_profile=get_profile("optimized").to_dict(),
    ).to_dict()

    md = build_comparison_markdown(baseline, optimized)

    assert "TTFT p50" in md
    assert "Throughput tok/s" in md
    assert "max_num_seqs" in md
