"""Agent 自动化测试用 Mock LLM（Task 8.2，不依赖真实 API）。"""

from __future__ import annotations

import json

from app.llm.types import ChatResult
from app.llm.types import ToolCall


SAMPLE_GIT_DIFF = """diff --git a/api.py b/api.py
--- a/api.py
+++ b/api.py
@@ -1 +1,3 @@
+password = "hardcoded"
+eval(user_input)
"""


class BlogPlanningMockLLM:
    """Project Manager 任务规划 Mock。"""

    model = "agent-mock-pm"

    def bind_tool_manager(self, tool_manager) -> None:
        return None

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        user = messages[-1].content or ""

        if "SOFTWARE_TEAM_TASK_PLAN_GOAL" in user:
            return ChatResult(
                model=self.model,
                content="构建企业知识库问答 API，支持文档上传、向量检索与对话。",
            )

        if "SOFTWARE_TEAM_TASK_PLAN" in user:
            tasks = [
                {
                    "title": "PRD 与验收标准",
                    "description": "输出 PRD.md",
                    "agent": "product",
                },
                {
                    "title": "架构设计",
                    "description": "输出 Architecture.md",
                    "agent": "architecture",
                },
                {
                    "title": "API 实现",
                    "description": "实现 upload / ask 接口",
                    "agent": "developer",
                },
                {
                    "title": "代码审查",
                    "description": "审查安全与规范",
                    "agent": "reviewer",
                },
                {
                    "title": "自动化测试",
                    "description": "pytest 覆盖核心 API",
                    "agent": "tester",
                },
            ]
            return ChatResult(
                model=self.model,
                content=json.dumps(tasks, ensure_ascii=False),
            )

        return ChatResult(model=self.model, content="[]")


class DeveloperToolMockLLM:
    """Developer Agent：首轮 tool_call，次轮文本结束。"""

    model = "agent-mock-developer"
    turn = 0

    def bind_tool_manager(self, tool_manager) -> None:
        return None

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        self.turn += 1

        if self.turn == 1:
            return ChatResult(
                model=self.model,
                tool_calls=[
                    ToolCall(
                        id="dev-1",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "src/knowledge_api.py",
                            "content": '"""Knowledge API."""\n\nVERSION = "0.1.0"\n',
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content="Implementation completed via code tool.",
        )


class ReviewerStructuredMockLLM:
    """Reviewer Agent：返回符合章节校验的 Markdown。"""

    model = "agent-mock-reviewer"

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        return ChatResult(
            model=self.model,
            content=(
                "# Review\n\n## 摘要\n\n发现 1 项安全问题。\n\n"
                "## 代码规范\n\n- 命名可改进\n\n"
                "## 安全问题\n\n- 硬编码密码\n\n"
                "## 性能问题\n\n- 无\n\n"
                "## 架构问题\n\n- 无\n\n"
                "## 修改建议汇总\n\n1. 移除硬编码密钥"
            ),
        )


class TesterToolMockLLM:
    """Tester Agent：写测试文件后结束。"""

    model = "agent-mock-tester"
    turn = 0

    def bind_tool_manager(self, tool_manager) -> None:
        return None

    def chat(self, messages, use_tools: bool = True) -> ChatResult:
        self.turn += 1

        if self.turn == 1:
            return ChatResult(
                model=self.model,
                tool_calls=[
                    ToolCall(
                        id="test-1",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "tests/test_api.py",
                            "content": "def test_health():\n    assert True\n",
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content="Tests written; see Test Report.",
        )
