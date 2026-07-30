#!/usr/bin/env python3
"""
Task 5.1 Demo：Project Manager Agent 生成任务列表。

用法：
    cd backend
    python -m applications.software_team.run_pm_demo
    python -m applications.software_team.run_pm_demo --requirement "开发一个博客系统"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_REQUIREMENT = "开发一个博客系统"


class BlogDemoMockLLM:
    """无外部 LLM 时演示博客系统任务规划。"""

    model = "demo-mock"

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(
        self,
        messages,
        use_tools=True,
    ):
        from app.llm.types import ChatResult

        user = messages[-1].content or ""

        if "SOFTWARE_TEAM_TASK_PLAN_GOAL" in user:

            body = (
                "构建一个支持文章发布、分类、评论与管理员后台的"
                "轻量级博客 Web 系统，优先 MVP 可部署。"
            )

            return ChatResult(model=self.model, content=body)

        if "SOFTWARE_TEAM_TASK_PLAN" in user:

            tasks = [
                {
                    "title": "博客 PRD 与用户故事",
                    "description": (
                        "定义文章、分类、标签、评论、用户角色与"
                        "验收标准，输出 PRD.md"
                    ),
                    "agent": "product",
                },
                {
                    "title": "博客系统架构设计",
                    "description": (
                        "设计前后端分离或单体结构、数据库模型、"
                        "API 清单与部署拓扑，输出 Architecture.md"
                    ),
                    "agent": "architecture",
                },
                {
                    "title": "博客核心功能开发",
                    "description": (
                        "实现文章 CRUD、分类、评论 API 与管理界面"
                    ),
                    "agent": "developer",
                },
                {
                    "title": "代码审查",
                    "description": (
                        "审查安全（XSS/鉴权）、性能与代码规范"
                    ),
                    "agent": "reviewer",
                },
                {
                    "title": "自动化测试",
                    "description": (
                        "编写 API 与关键路径 pytest，覆盖发布与评论流程"
                    ),
                    "agent": "tester",
                },
                {
                    "title": "容器化与部署",
                    "description": (
                        "提供 Docker Compose、环境变量说明与健康检查"
                    ),
                    "agent": "devops",
                },
            ]

            return ChatResult(
                model=self.model,
                content=json.dumps(tasks, ensure_ascii=False),
            )

        return ChatResult(
            model=self.model,
            content="[]",
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Project Manager Agent Demo (Task 5.1)",
    )

    parser.add_argument(
        "--requirement",
        default=DEFAULT_REQUIREMENT,
    )

    args = parser.parse_args()

    from app.agents.software_team.manager_agent import ProjectManagerAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    config = AgentConfig(
        max_iterations=1,
        enable_mcp=False,
        enable_rag=False,
        enable_trace=False,
    )

    pm = ProjectManagerAgent(
        config=config,
        client=BlogDemoMockLLM(),
    )

    result = pm.run(
        AgentContext(
            session_id="demo-software-team-pm",
            user_message=args.requirement,
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
