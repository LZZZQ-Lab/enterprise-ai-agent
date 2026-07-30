#!/usr/bin/env python3
"""
Demo 06 — 模型路由与推理基础设施

Part A: Model Router — 按任务类型自动选模（Registry + RouterEngine）
Part B: Inference Gateway — 统一推理入口 + Token 统计（Mock Backend）

全程离线，无需 GPU / API Key。

用法:
    python examples/demo_06_infra.py
"""

from __future__ import annotations

from _bootstrap import bootstrap


def demo_model_router() -> None:
    from app.model_registry.manager import ModelRegistryManager
    from app.model_registry.repository import ModelRegistryRepository
    from app.router.engine import RouterEngine
    from app.router.policy import build_default_policy_map
    from app.router.types import RoutingContext
    from app.router.types import TaskKind

    print("--- Part A: Model Router ---\n")

    registry = ModelRegistryManager(
        repository=ModelRegistryRepository(),
        auto_load=True,
    )
    engine = RouterEngine(
        registry=registry,
        policies=build_default_policy_map(),
        long_context_threshold=6000,
    )

    scenarios = [
        ("日常对话", "你好，介绍一下 Enterprise AI Platform"),
        (
            "代码生成",
            "请用 Python 实现 def fib(n): 并修复 bug\n```python\npass\n```",
        ),
        ("数学推理", "求解方程 2x + 5 = 13，写出步骤"),
        ("长上下文", "x" * 7000),
    ]

    for label, prompt in scenarios:
        report = engine.route(RoutingContext(prompt=prompt))
        print(f"[{label}]")
        print(f"  task_type : {report.task_type.value}")
        print(f"  policy    : {report.policy_name}")
        print(f"  selected  : {report.selected_registry_name}")
        if report.winner:
            print(f"  model_id  : {report.winner.model_id}")
        print()

    explicit = engine.route(
        RoutingContext(
            prompt="hello",
            task=TaskKind.CODE,
        )
    )
    print("[显式任务 CODE]")
    print(f"  selected: {explicit.selected_registry_name}")
    print(f"  source  : {explicit.prompt_signals.get('task_source')}")
    print()


def demo_inference_gateway() -> None:
    from app.gateway.service import InferenceGateway
    from app.gateway.stats import get_token_stats
    from app.gateway.stats import reset_token_stats
    from app.gateway.types import InferenceBackendKind
    from app.llm.types import Message
    from _mock import DemoGatewayBackend

    print("--- Part B: Inference Gateway ---\n")

    reset_token_stats()

    backend = DemoGatewayBackend()
    gateway = InferenceGateway(
        backend=backend,
        backend_kind=InferenceBackendKind.OPENAI,
    )

    payload = gateway.chat(
        [Message(role="user", content="Route this via gateway mock.")],
        use_tools=False,
    )

    stats = get_token_stats()

    print(f"Answer        : {payload.result.content}")
    print(f"Backend       : {gateway.backend_kind.value}")
    print(f"Total requests: {stats.total_requests}")
    print(f"Total tokens  : {stats.total_tokens}")
    print(f"By backend    : {dict(stats.by_backend)}")
    print()


def main() -> None:
    bootstrap()

    print("=== Demo 06: LLM Infrastructure (Router + Gateway) [Mock] ===\n")

    demo_model_router()
    demo_inference_gateway()

    print("Done.")


if __name__ == "__main__":
    main()
