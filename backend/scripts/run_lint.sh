#!/usr/bin/env bash
# Task 8.5：Ruff lint（CI 门禁）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_ROOT}"

echo "==> ruff check"
# tests/ 在仓库根目录（Task 9.1）；其余路径相对 backend/
python -m ruff check app ../tests benchmark loadtest scripts "$@"

echo "Lint OK"
