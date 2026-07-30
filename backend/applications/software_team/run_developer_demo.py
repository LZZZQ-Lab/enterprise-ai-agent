#!/usr/bin/env python3
"""
Task 5.4 Demo：Developer Agent 经 Tool 生成代码。

用法：
    cd backend
    python -m applications.software_team.run_developer_demo
    python -m applications.software_team.run_developer_demo --workspace ./tmp-dev-demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


SAMPLE_ARCHITECTURE = """# System Design — 博客

## 技术选型
FastAPI + PostgreSQL

## 数据库设计
posts, users, comments

## 接口设计
GET/POST /api/v1/posts
"""

SAMPLE_TASKS = [
    {
        "title": "项目骨架",
        "agent": "developer",
        "description": "README 与 src/main.py 入口",
    },
    {
        "title": "健康检查",
        "agent": "developer",
        "description": "GET /health 占位（后续迭代）",
    },
]


class DeveloperDemoMockLLM:
    """两轮 Tool Call 后结束。"""

    model = "demo-mock-developer"
    _step = 0

    def bind_tool_manager(self, tool_manager) -> None:

        self._tool_manager = tool_manager

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult
        from app.llm.types import ToolCall

        self._step += 1

        if self._step == 1:

            return ChatResult(
                model=self.model,
                content="Reading architecture and scaffolding project.",
                tool_calls=[
                    ToolCall(
                        id="tc1",
                        name="filesystem",
                        arguments={
                            "action": "list",
                            "path": ".",
                        },
                    ),
                    ToolCall(
                        id="tc2",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "src/app.py",
                            "content": (
                                '"""Blog API placeholder."""\n\n'
                                "def health() -> dict:\n"
                                '    return {"status": "ok"}\n'
                            ),
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content=(
                "已通过 code tool 写入 src/app.py；"
                "请查看 Code Change History。"
            ),
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Developer Agent Demo (Task 5.4)",
    )

    parser.add_argument(
        "--workspace",
        default="./tmp-dev-demo",
    )

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    (workspace / "docs").mkdir(exist_ok=True)
    (workspace / "docs" / "architecture.md").write_text(
        SAMPLE_ARCHITECTURE,
        encoding="utf-8",
    )

    from app.agents.software_team.developer_agent import DeveloperAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    agent = DeveloperAgent(
        config=AgentConfig(
            max_iterations=5,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=False,
        ),
        client=DeveloperDemoMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-developer",
            user_message="根据架构与任务列表生成博客 MVP 代码骨架",
            metadata={"workspace_dir": str(workspace)},
            shared_context={
                "tasks": SAMPLE_TASKS,
                "architecture": SAMPLE_ARCHITECTURE,
            },
        )
    )

    print(result.content)
    print("\n--- workspace files ---")

    for path in sorted(workspace.rglob("*")):

        if path.is_file():

            print(path.relative_to(workspace))


if __name__ == "__main__":

    main()
