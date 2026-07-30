#!/usr/bin/env python3
"""
Demo 03 — Agent Tool Calling

ChatAgent + time Tool：Mock LLM 第一轮触发 Tool，第二轮返回最终答案。

用法:
    python examples/demo_03_agent.py
    python examples/demo_03_agent.py --live   # 需 API Key
"""

from __future__ import annotations

import argparse

from _bootstrap import bootstrap


def run_mock() -> None:
    from app.agents.chat_agent import ChatAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig
    from app.tools.factory import ToolFactory
    from _mock import DemoToolCallingLLM

    print("=== Demo 03: Agent Tool Calling [Mock] ===\n")

    ToolFactory.initialize()

    config = AgentConfig(
        max_iterations=5,
        enable_mcp=False,
        enable_trace=False,
        enable_planner=False,
    )

    agent = ChatAgent(
        config=config,
        client=DemoToolCallingLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-03",
            user_message="请告诉我现在的时间。",
            agent_name="chat",
        )
    )

    print(f"Success : {result.success}")
    print(f"Model   : {result.model}")
    print(f"Answer  :\n{result.content}\n")


def run_live() -> None:
    from app.agents.chat_agent import ChatAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig
    from app.tools.factory import ToolFactory

    print("=== Demo 03: Agent Tool Calling [Live] ===\n")

    ToolFactory.initialize()

    config = AgentConfig(
        max_iterations=5,
        enable_mcp=False,
        enable_trace=False,
        enable_planner=False,
    )

    agent = ChatAgent(config=config)

    result = agent.run(
        AgentContext(
            session_id="demo-03-live",
            user_message="请用 time 工具告诉我当前时间。",
            agent_name="chat",
        )
    )

    print(f"Success : {result.success}")
    print(f"Model   : {result.model}")
    print(f"Answer  :\n{result.content}\n")


def main() -> None:
    bootstrap()

    parser = argparse.ArgumentParser(description="Demo 03 — Agent Tool Calling")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    if args.live:
        run_live()
    else:
        run_mock()

    print("Done.")


if __name__ == "__main__":
    main()
