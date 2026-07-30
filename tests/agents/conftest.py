"""Task 8.2 Agent 自动化测试 fixtures。"""

from __future__ import annotations

import pytest

from app.config import AgentConfig

USER_REQUEST = "开发一个企业知识库问答 API，支持文档上传与检索增强对话"


@pytest.fixture
def agent_team_config() -> AgentConfig:
    return AgentConfig(
        max_iterations=3,
        enable_mcp=False,
        enable_rag=False,
        enable_knowledge_tool=False,
        enable_trace=False,
        enable_planner=False,
    )


@pytest.fixture
def user_request() -> str:
    return USER_REQUEST
