"""Shared paths for tests (Task 8.1)."""

from __future__ import annotations

from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"

KNOWLEDGE_FIXTURES = TESTS_ROOT / "fixtures" / "knowledge"
MCP_DEMO_FIXTURES = TESTS_ROOT / "fixtures" / "mcp_demo"
