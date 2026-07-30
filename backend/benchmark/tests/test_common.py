"""Task 2.6: percentile helper tests."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from benchmark.common import percentile  # noqa: E402


def test_percentile_median() -> None:
    assert percentile([10.0, 20.0, 30.0], 50) == 20.0


def test_percentile_single() -> None:
    assert percentile([42.0], 95) == 42.0
