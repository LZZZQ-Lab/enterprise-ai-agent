#!/usr/bin/env python3
"""
企业项目方案 Multi-Agent Demo。

流程：ManagerAgent → Planner → Research → Writer → Reviewer

用法（仓库 backend 目录）：
    python -m applications.enterprise_proposal.run_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_TASK = (
    "为制造业客户设计一套「企业 AI 知识库 + 智能客服」"
    "落地项目方案，周期 3 个月，需考虑私有化部署与合规。"
)


class DemoMockLLM:
    """无外部 LLM 时的演示回复。"""

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(
        self,
        messages,
        use_tools=True,
    ):
        from app.llm.types import ChatResult

        user = (messages[-1].content or "").lower()

        if "请为以下用户任务制定" in user:

            body = (
                "## 目标\n"
                "建设企业知识库 RAG 与智能客服 Agent。\n\n"
                "## 阶段\n"
                "1. 需求与数据治理\n"
                "2. 知识库与模型部署\n"
                "3. 联调上线与培训\n\n"
                "## 里程碑\n"
                "- M1: 知识库 MVP\n"
                "- M2: 客服 Agent 试点\n"
                "- M3: 生产发布\n\n"
                "## 风险\n"
                "- 数据质量与权限\n"
                "- GPU/私有化资源"
            )

        elif "请针对下列任务" in user:

            body = (
                "## 调研摘要\n"
                "- 行业：制造业售后与内部 IT 知识场景\n"
                "- 合规：数据不出域、审计日志\n"
                "- 技术：Qwen + vLLM + 向量库 Chroma\n"
                "- 集成：现有工单系统 API"
            )

        elif "请撰写完整" in user:

            body = (
                "# 项目方案（初稿）\n\n"
                "## 概述\n"
                "三个月内交付可私有化部署的知识库问答与客服 Agent。\n\n"
                "## 范围\n"
                "文档入库、RAG 检索、Tool 调用、运维监控。\n\n"
                "## 实施步骤\n"
                "按三阶段推进，每阶段有明确交付物。\n\n"
                "## 时间线\n"
                "第1月治理与 MVP；第2月 Agent；第3月上线。"
            )

        elif "请审阅下列" in user:

            body = (
                "# 项目方案（审定版）\n\n"
                "## 概述\n"
                "面向制造业的 Enterprise AI 知识库与智能客服方案，"
                "3 个月分阶段交付，支持私有化与合规审计。\n\n"
                "## 实施路线\n"
                "阶段一：需求与数据治理；阶段二：RAG/Agent 集成；"
                "阶段三：试点与生产发布。\n\n"
                "## 交付物\n"
                "知识库、Agent 服务、部署文档、培训与 SLA 建议。"
            )

        else:

            body = "（Demo）已处理子任务。"

        return ChatResult(
            model="demo-mock",
            content=body,
        )


def run_demo(
    task: str,
    session_id: str = "demo-proposal",
) -> str:
    from app.agents.manager_agent import ManagerAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    config = AgentConfig(
        max_iterations=3,
        enable_mcp=False,
        enable_rag=False,
        enable_knowledge_tool=False,
        enable_trace=False,
        enable_planner=False,
    )

    manager = ManagerAgent(
        config=config,
        client=DemoMockLLM(),
    )

    result = manager.run(
        AgentContext(
            session_id=session_id,
            user_message=task,
        )
    )

    if not result.success:

        raise RuntimeError(result.content)

    return result.content


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Multi-Agent 项目方案 Demo",
    )

    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="用户任务描述",
    )

    args = parser.parse_args()

    output = run_demo(args.task)

    print(output)


if __name__ == "__main__":

    main()
