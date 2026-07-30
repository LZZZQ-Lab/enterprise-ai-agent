"""Shared path bootstrap for examples/ demos (Task 9.4)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
OUTPUT_ROOT = Path(__file__).resolve().parent / "_output"


def bootstrap() -> tuple[Path, Path]:
    """Insert backend + repo root on sys.path for app/core/llm imports."""

    for path in (BACKEND_ROOT, REPO_ROOT):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    return REPO_ROOT, BACKEND_ROOT
