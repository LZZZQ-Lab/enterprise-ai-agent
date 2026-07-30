#!/usr/bin/env bash
# Task 8.3: run LLM benchmark suite and emit benchmark_report.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MOCK="${BENCHMARK_MOCK:-}"
ARGS=()

if [[ "${1:-}" == "--mock" ]] || [[ "$MOCK" == "1" ]]; then
  ARGS+=(--mock)
  shift || true
fi

python -m benchmark.suite_runner "${ARGS[@]}" "$@"

echo "Done. See artifacts/benchmark_report.md"
