#!/usr/bin/env python3
"""
MCP 工具生态 Demo。

流程：MCP Server → Adapter → ToolRegistry → Agent

用法：
    cd backend
    python -m applications.mcp_demo.run_demo
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))

WORKSPACE = (
    BACKEND_ROOT
    / "tests"
    / "fixtures"
    / "mcp_demo"
    / "workspace"
)


def run_demo() -> None:

    from app.agents.chat_agent import ChatAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig
    from app.llm.types import ChatResult
    from app.llm.types import ToolCall
    from app.mcp.tools import setup_enterprise_mcp_demo
    from app.tools.registry import ToolRegistry
    from app.tools.types import ToolContext

    bridge = setup_enterprise_mcp_demo(
        workspace_root=WORKSPACE,
    )

    tool_name = "enterprise-demo.fs_read_file"

    assert tool_name in ToolRegistry._tools

    direct = ToolRegistry.get(tool_name).execute(
        ToolContext(
            tool_name=tool_name,
            arguments={
                "path": "docs/project_brief.txt",
            },
        )
    )

    print("=== MCP Tool (Registry) ===")
    print(direct.content)
    print()

    class DemoLLM:
        def __init__(self) -> None:

            self._round = 0

        def bind_tool_manager(self, _manager) -> None:

            return None

        def chat(self, messages, use_tools=True):

            self._round += 1

            if self._round == 1:

                return ChatResult(
                    model="demo",
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="1",
                            name=tool_name,
                            arguments={
                                "path": "docs/project_brief.txt",
                            },
                        )
                    ],
                )

            return ChatResult(
                model="demo",
                content="目标：上线企业知识库与智能客服 Agent。",
            )

    config = AgentConfig(
        max_iterations=3,
        enable_mcp=True,
        mcp_servers=["enterprise-demo"],
        enable_trace=False,
        enable_planner=False,
        enable_knowledge_tool=False,
    )

    agent = ChatAgent(
        config=config,
        client=DemoLLM(),
        mcp_server_manager=bridge.manager,
    )

    agent.tool_manager.bind_mcp(bridge.manager)

    result = agent.execute(
        AgentContext(
            session_id="mcp-demo",
            user_message="请读取项目简报并总结目标",
        )
    )

    print("=== Agent + MCP ===")
    print("success:", result.success)
    print("tools registered:", bridge.sync_to_tool_registry())


if __name__ == "__main__":

    run_demo()
