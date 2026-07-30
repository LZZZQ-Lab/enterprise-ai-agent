#!/usr/bin/env bash
# Task 8.7: structured logging query demo
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python scripts/logging_query_demo.py
python -m pytest observability/logging/tests/test_logging.py -q
