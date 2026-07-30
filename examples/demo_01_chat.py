#!/usr/bin/env python3
"""
Demo 01 — 基础 LLM 调用

展示 BaseLLM.chat() 与 Message 组装。默认 Mock 模式，无需 API Key。

用法:
    python examples/demo_01_chat.py
    python examples/demo_01_chat.py --live   # 需配置 backend/.env
"""

from __future__ import annotations

import argparse

from _bootstrap import bootstrap


def run_mock() -> None:
    from app.llm.types import Message
    from _mock import DemoChatLLM

    print("=== Demo 01: 基础 LLM 调用 [Mock] ===\n")

    client = DemoChatLLM()
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Enterprise AI Platform 是什么？"),
    ]

    result = client.chat(messages, use_tools=False)

    print(f"Model : {result.model}")
    print(f"Answer:\n{result.content}\n")


def run_live() -> None:
    from app.llm.factory import get_llm_client
    from app.llm.types import Message

    print("=== Demo 01: 基础 LLM 调用 [Live] ===\n")

    client = get_llm_client()
    messages = [
        Message(role="user", content="用一句话介绍 Enterprise AI Platform。"),
    ]
    result = client.chat(messages, use_tools=False)

    print(f"Model : {result.model}")
    print(f"Answer:\n{result.content}\n")


def main() -> None:
    bootstrap()

    parser = argparse.ArgumentParser(description="Demo 01 — Basic LLM chat")
    parser.add_argument(
        "--live",
        action="store_true",
        help="使用真实 LLM（需 backend/.env 中 API_KEY）",
    )
    args = parser.parse_args()

    if args.live:
        run_live()
    else:
        run_mock()

    print("Done.")


if __name__ == "__main__":
    main()
