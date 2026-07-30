#!/usr/bin/env python3
"""
Task 5.7 Demo：DevOps Agent 生成 Docker 配置并 Build/Deploy。

用法：
    cd backend
    python -m applications.software_team.run_devops_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


class DevOpsDemoMockLLM:
    model = "demo-mock-devops"
    _step = 0

    def bind_tool_manager(self, tool_manager) -> None:

        self._tm = tool_manager

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult
        from app.llm.types import ToolCall

        self._step += 1

        if self._step == 1:

            return ChatResult(
                model=self.model,
                content="Writing Docker artifacts.",
                tool_calls=[
                    ToolCall(
                        id="d1",
                        name="code",
                        arguments={
                            "action": "write",
                            "path": "Dockerfile",
                            "content": (
                                "FROM python:3.11-slim\n"
                                "WORKDIR /app\n"
                                'CMD ["python", "-c", "print(\'demo\')"]\n'
                            ),
                        },
                    ),
                    ToolCall(
                        id="d2",
                        name="environment",
                        arguments={
                            "action": "write",
                            "path": ".env.example",
                            "content": "APP_ENV=demo\nPORT=8000\n",
                        },
                    ),
                ],
            )

        return ChatResult(
            model=self.model,
            content="Artifacts ready; build/deploy runs in agent finalize step.",
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="DevOps Agent Demo (Task 5.7)",
    )

    parser.add_argument(
        "--workspace",
        default="./tmp-devops-demo",
    )

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    from app.agents.software_team.devops_agent import DevOpsAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    agent = DevOpsAgent(
        config=AgentConfig(
            max_iterations=3,
            enable_trace=False,
            enable_mcp=False,
        ),
        client=DevOpsDemoMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-devops",
            user_message="为博客 API 生成 Docker 部署并 build/deploy",
            metadata={
                "workspace_dir": str(workspace),
                "devops_simulate": True,
            },
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
