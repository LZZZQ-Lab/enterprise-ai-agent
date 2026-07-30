#!/usr/bin/env bash
# Task 8.6: security capability demo
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python scripts/security_demo.py
python -m pytest security/tests/test_security.py -q
