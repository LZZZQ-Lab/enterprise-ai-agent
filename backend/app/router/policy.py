"""
RoutePolicy：按任务类型定义模型优先级与权重。
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field

from app.router.types import TaskKind


class RoutePolicy(BaseModel):
    """
    单任务路由策略。

    ``preferred_models`` 为 Registry ``name`` 列表，按优先级排序。
    """

    name: str
    task_type: TaskKind
    preferred_models: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    min_context_length: int = 0
    cost_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    latency_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    preference_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    fallback_model: str = "qwen2.5-0.5b-instruct"

    def normalized_weights(
        self,
        *,
        prefer_low_cost: bool,
        prefer_low_latency: bool,
    ) -> tuple[float, float, float]:
        cost_w = self.cost_weight
        latency_w = self.latency_weight
        pref_w = self.preference_weight

        if prefer_low_cost:
            cost_w *= 1.5
        if prefer_low_latency:
            latency_w *= 1.5

        total = cost_w + latency_w + pref_w
        if total <= 0:
            return 1 / 3, 1 / 3, 1 / 3
        return cost_w / total, latency_w / total, pref_w / total


DEFAULT_ROUTE_POLICIES: list[RoutePolicy] = [
    RoutePolicy(
        name="chat-default",
        task_type=TaskKind.CHAT,
        preferred_models=[
            "qwen2.5-0.5b-instruct",
            "qwen2.5-7b-instruct",
            "gpt-4o-mini",
        ],
        required_capabilities=["chat"],
        cost_weight=0.25,
        latency_weight=0.45,
        preference_weight=0.30,
        fallback_model="qwen2.5-0.5b-instruct",
    ),
    RoutePolicy(
        name="code-deepseek",
        task_type=TaskKind.CODE,
        preferred_models=["deepseek-coder", "gpt-4o"],
        required_capabilities=["code"],
        cost_weight=0.30,
        latency_weight=0.30,
        preference_weight=0.40,
        fallback_model="deepseek-coder",
    ),
    RoutePolicy(
        name="math-qwen",
        task_type=TaskKind.MATH,
        preferred_models=["qwen2.5-math", "deepseek-reasoner"],
        required_capabilities=["math"],
        cost_weight=0.25,
        latency_weight=0.35,
        preference_weight=0.40,
        fallback_model="qwen2.5-math",
    ),
    RoutePolicy(
        name="long-context-llama",
        task_type=TaskKind.LONG_CONTEXT,
        preferred_models=[
            "llama-3.1-8b-instruct",
            "llama-3.1-70b-instruct",
            "qwen2.5-72b-instruct",
        ],
        required_capabilities=["long_context"],
        min_context_length=65536,
        cost_weight=0.40,
        latency_weight=0.20,
        preference_weight=0.40,
        fallback_model="llama-3.1-8b-instruct",
    ),
]


def build_default_policy_map() -> dict[TaskKind, RoutePolicy]:
    return {policy.task_type: policy for policy in DEFAULT_ROUTE_POLICIES}
