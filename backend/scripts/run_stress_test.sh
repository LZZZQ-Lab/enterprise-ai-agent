#!/usr/bin/env bash
# Task 8.4: Locust stress test — API / Agent Workflow / Inference Gateway
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pip install -q -r requirements-loadtest.txt

MOCK=0
QUICK=0
EXTRA=()

for arg in "$@"; do
  case "$arg" in
    --mock) MOCK=1 ;;
    --quick) QUICK=1 ;;
    *) EXTRA+=("$arg") ;;
  esac
done

CMD=(python -m loadtest.run_stress)
[[ "$MOCK" == "1" ]] && CMD+=(--mock)
[[ "$QUICK" == "1" ]] && CMD+=(--quick)
CMD+=("${EXTRA[@]}")

"${CMD[@]}"
echo "Done. See artifacts/stress_test_report.md"
