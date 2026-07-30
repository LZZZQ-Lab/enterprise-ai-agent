"""Task 2.6: shared benchmark utilities."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Iterator

BENCHMARK_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = BENCHMARK_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent
RESULTS_DIR = BENCHMARK_ROOT / "results"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
DOCS_PERFORMANCE = REPO_ROOT / "docs" / "performance.md"
BENCHMARK_REPORT = ARTIFACTS_DIR / "benchmark_report.md"

DEFAULT_PROMPT = "请用三句话介绍企业级 AI 助手平台可以做什么。"
DEFAULT_MODEL_LABEL = "Qwen2.5"

# Task 8.3: canonical backend ids for comparison reports
BACKEND_QWEN = "qwen"
BACKEND_VLLM = "vllm"
BACKEND_OPENAI = "openai"
SUITE_BACKENDS = (BACKEND_QWEN, BACKEND_VLLM, BACKEND_OPENAI)

BACKEND_ALIASES: dict[str, str] = {
    "transformers": BACKEND_QWEN,
    "local": BACKEND_QWEN,
}


def normalize_backend(backend: str) -> str:
    key = backend.strip().lower()
    return BACKEND_ALIASES.get(key, key)


def backend_display_name(backend: str) -> str:
    labels = {
        BACKEND_QWEN: "Qwen (Transformers)",
        BACKEND_VLLM: "vLLM",
        BACKEND_OPENAI: "OpenAI",
    }
    return labels.get(normalize_backend(backend), backend)


@dataclass
class LatencyMetrics:
    backend: str
    model: str
    runs: int
    ttft_ms_p50: float
    ttft_ms_p95: float
    total_ms_p50: float
    total_ms_p95: float
    tokens_per_sec_p50: float
    completion_tokens_avg: float
    gpu_memory_mb: dict[str, float | None]
    notes: str = ""


@dataclass
class ThroughputMetrics:
    backend: str
    model: str
    concurrent_requests: int
    total_requests: int
    wall_time_sec: float
    total_completion_tokens: int
    requests_per_sec: float
    tokens_per_sec: float
    gpu_memory_mb: dict[str, float | None]
    notes: str = ""


def ensure_results_dir() -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def gpu_memory_snapshot() -> dict[str, float | None]:
    """Used / total GPU memory (MiB) via nvidia-smi."""

    if shutil.which("nvidia-smi") is None:
        return {"used_mib": None, "total_mib": None}

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        )
        line = out.strip().splitlines()[0]
        used, total = (float(x.strip()) for x in line.split(","))
        return {"used_mib": used, "total_mib": total}
    except (subprocess.SubprocessError, OSError, ValueError):
        return {"used_mib": None, "total_mib": None}


def torch_gpu_memory_snapshot() -> dict[str, float | None]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"allocated_mib": None, "reserved_mib": None}

        return {
            "allocated_mib": torch.cuda.memory_allocated() / (1024**2),
            "reserved_mib": torch.cuda.memory_reserved() / (1024**2),
        }
    except ImportError:
        return {"allocated_mib": None, "reserved_mib": None}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def estimate_token_count(text: str) -> int:
    """Rough token estimate when API does not return usage."""

    if not text:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = max(0, len(text) - cjk)
    return max(1, int(cjk * 1.2 + other / 4))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_sse_data_lines(raw_line: bytes) -> Iterator[dict[str, Any]]:
    line = raw_line.decode("utf-8", errors="replace").strip()
    if not line.startswith("data:"):
        return
    data = line[5:].strip()
    if data == "[DONE]":
        return
    try:
        yield json.loads(data)
    except json.JSONDecodeError:
        return


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def merge_gpu_snapshots(*snapshots: dict[str, float | None]) -> dict[str, float | None]:
    merged: dict[str, float | None] = {}
    for snap in snapshots:
        merged.update(snap)
    return merged
