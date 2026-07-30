"""Task 8.3: benchmark suite and report tests."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchmark.build_benchmark_report import build_benchmark_report  # noqa: E402
from benchmark.common import BACKEND_OPENAI  # noqa: E402
from benchmark.common import BACKEND_QWEN  # noqa: E402
from benchmark.common import BACKEND_VLLM  # noqa: E402
from benchmark.common import SUITE_BACKENDS  # noqa: E402
from benchmark.common import normalize_backend  # noqa: E402
from benchmark.suite_runner import main as run_suite_main  # noqa: E402


def test_normalize_backend_aliases() -> None:
    assert normalize_backend("transformers") == BACKEND_QWEN
    assert normalize_backend("local") == BACKEND_QWEN
    assert normalize_backend("vllm") == BACKEND_VLLM
    assert normalize_backend("openai") == BACKEND_OPENAI


def test_suite_mock_generates_report(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    report_path = tmp_path / "benchmark_report.md"
    results_dir.mkdir()

    rc = run_suite_main(
        [
            "--mock",
            "--backends",
            "qwen",
            "vllm",
            "openai",
            "--results-dir",
            str(results_dir),
            "--report",
            str(report_path),
        ]
    )
    assert rc == 0
    assert report_path.is_file()

    text = report_path.read_text(encoding="utf-8")
    assert "Task 8.3" in text
    assert "Qwen (Transformers)" in text
    assert "vLLM" in text
    assert "OpenAI" in text
    assert "TTFT" in text
    assert "Throughput" in text

    for backend in SUITE_BACKENDS:
        assert (results_dir / f"latency_{backend}.json").is_file()
        assert (results_dir / f"throughput_{backend}.json").is_file()


def test_build_report_from_existing_results(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    rc = run_suite_main(
        [
            "--mock",
            "--backends",
            "vllm",
            "openai",
            "--results-dir",
            str(results_dir),
            "--skip-report",
        ]
    )
    assert rc == 0

    md = build_benchmark_report(results_dir)
    assert "vLLM" in md
    assert "OpenAI" in md
    assert "| Backend |" in md
