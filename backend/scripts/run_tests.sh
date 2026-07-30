#!/usr/bin/env bash
# Task 8.1：运行测试并生成报告
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_ROOT}"

mkdir -p artifacts

MARKERS="${TEST_MARKERS:-not integration}"
EXTRA_ARGS=("$@")

echo "==> pytest -m '${MARKERS}'"
python -m pytest \
  -m "${MARKERS}" \
  --junitxml=artifacts/test-report.xml \
  --tb=short \
  "${EXTRA_ARGS[@]}"

echo
echo "Report: ${BACKEND_ROOT}/artifacts/test-report.xml"
