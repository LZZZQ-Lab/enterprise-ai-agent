"""Task 7.2 Model Router 测试。"""

from __future__ import annotations

from app.model_registry.manager import ModelRegistryManager
from app.model_registry.repository import ModelRegistryRepository
from app.router.engine import RouterEngine
from app.router.policy import build_default_policy_map
from app.router.types import RoutingContext
from app.router.types import TaskKind


def _engine() -> RouterEngine:
    repo = ModelRegistryRepository()
    registry = ModelRegistryManager(repository=repo, auto_load=True)
    return RouterEngine(
        registry=registry,
        policies=build_default_policy_map(),
        long_context_threshold=6000,
    )


def test_route_chat_to_qwen() -> None:
    engine = _engine()
    report = engine.route(
        RoutingContext(prompt="你好，介绍一下你自己"),
    )
    assert report.task_type == TaskKind.CHAT
    assert report.selected_registry_name.startswith("qwen2.5")
    assert report.policy_name == "chat-default"
    assert report.winner is not None
    assert report.candidates


def test_route_code_to_deepseek_coder() -> None:
    engine = _engine()
    prompt = (
        "请用 Python 实现 def fib(n): 并修复这个 bug\n"
        "```python\npass\n```"
    )
    report = engine.route(RoutingContext(prompt=prompt))
    assert report.task_type == TaskKind.CODE
    assert report.selected_registry_name == "deepseek-coder"


def test_route_math_to_qwen_math() -> None:
    engine = _engine()
    report = engine.route(
        RoutingContext(prompt="求解方程 2x + 5 = 13，并证明步骤"),
    )
    assert report.task_type == TaskKind.MATH
    assert report.selected_registry_name == "qwen2.5-math"


def test_route_long_context_to_llama() -> None:
    engine = _engine()
    report = engine.route(
        RoutingContext(prompt="x" * 7000),
    )
    assert report.task_type == TaskKind.LONG_CONTEXT
    assert "llama" in report.selected_registry_name


def test_explicit_task_overrides_prompt() -> None:
    engine = _engine()
    report = engine.route(
        RoutingContext(
            prompt="hello",
            task=TaskKind.CODE,
        ),
    )
    assert report.task_type == TaskKind.CODE
    assert report.prompt_signals.get("task_source") == "explicit"
    assert report.selected_registry_name == "deepseek-coder"


def test_prefer_low_cost_in_report_weights() -> None:
    engine = _engine()
    base = engine.route(RoutingContext(prompt="chat"))
    biased = engine.route(
        RoutingContext(
            prompt="chat",
            prefer_low_cost=True,
        ),
    )
    assert biased.cost_weight > base.cost_weight


def test_routing_report_summary() -> None:
    engine = _engine()
    report = engine.route(RoutingContext(task=TaskKind.MATH, prompt="1+1"))
    text = report.summary()
    assert "math" in text
    assert "qwen2.5-math" in text
