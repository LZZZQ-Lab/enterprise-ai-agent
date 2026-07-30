"""Pytest 公共 fixtures 与自动 marker（Task 8.1）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AgentConfig
from core.tools import ToolFactory

from tests.fixtures.mock_llm import MockLLM


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """按目录自动打 unit / integration / e2e marker。"""

    for item in items:
        path = Path(str(item.fspath)).as_posix()

        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/tests/e2e/" in path:
            item.add_marker(pytest.mark.e2e)
        elif "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/agents/" in path:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def agent_config() -> AgentConfig:
    """测试用 Agent 配置，避免依赖外部 LLM。"""

    return AgentConfig(
        max_iterations=1,
        enable_mcp=False,
        enable_rag=False,
        enable_trace=False,
        enable_planner=False,
    )


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM()


@pytest.fixture(autouse=True)
def initialize_tools() -> None:
    """每个测试前确保 Tool 已注册。"""

    ToolFactory.initialize()
