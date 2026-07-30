"""Task 2.6 entrypoint (repo benchmark/ → backend/benchmark)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

if __name__ == "__main__":
    runpy.run_module("benchmark.latency_test", run_name="__main__")
