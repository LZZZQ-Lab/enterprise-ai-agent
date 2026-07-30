#!/usr/bin/env bash
# Task 9.4 — 运行全部 Mock Demo
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

DEMOS=(
  demo_01_chat.py
  demo_02_rag.py
  demo_03_agent.py
  demo_04_workflow.py
  demo_05_software_team.py
  demo_06_infra.py
)

echo "==> Enterprise AI Platform — run all Mock demos"
echo "    ROOT=${ROOT}"
echo

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi

for demo in "${DEMOS[@]}"; do
  echo "========================================"
  echo ">>> ${PYTHON_BIN} examples/${demo}"
  echo "========================================"
  "${PYTHON_BIN}" "examples/${demo}"
  echo
done

echo "All ${#DEMOS[@]} demos completed."
