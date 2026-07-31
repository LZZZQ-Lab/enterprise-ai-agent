#!/usr/bin/env bash
# Task 8.2：运行 Agent 自动化测试并生成报告
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_ROOT}"

mkdir -p artifacts

echo "==> pytest ../tests/agents"
python -m pytest ../tests/agents -v --tb=short

echo
echo "Agent Test Report: ${BACKEND_ROOT}/artifacts/agent_test_report.md"
