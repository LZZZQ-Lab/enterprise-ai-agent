#!/usr/bin/env python3
"""
Task 5.6 Demo：Tester Agent 生成测试并运行 pytest。

用法：
    cd backend
    python -m applications.software_team.run_tester_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


class TesterDemoMockLLM:
    model = "demo-mock-tester"
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
                content="Writing unit and API tests.",
                tool_calls=[
                    ToolCall(
                        id="t1",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "tests/test_unit_demo.py",
                            "content": (
                                "def test_demo_unit():\n"
                                "    assert True\n"
                            ),
                        },
                    ),
                    ToolCall(
                        id="t2",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "tests/test_api_demo.py",
                            "content": (
                                "def test_demo_api_path():\n"
                                '    assert "/api/v1" in "/api/v1/posts"\n'
                            ),
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content="Tests written; pytest will run automatically.",
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Tester Agent Demo (Task 5.6)",
    )

    parser.add_argument(
        "--workspace",
        default="./tmp-tester-demo",
    )

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    from app.agents.software_team.tester_agent import TesterAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    agent = TesterAgent(
        config=AgentConfig(
            max_iterations=4,
            enable_mcp=False,
            enable_trace=False,
        ),
        client=TesterDemoMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-tester",
            user_message="为博客 API 生成单元测试与 API 测试",
            metadata={"workspace_dir": str(workspace)},
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
