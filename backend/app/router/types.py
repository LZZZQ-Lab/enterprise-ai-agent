"""
Model Router 类型与 Routing Report（Task 7.2）。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from app.model_registry.models import ModelInfo


class TaskKind(str, Enum):
    """路由任务类型。"""

    CHAT = "chat"
    CODE = "code"
    MATH = "math"
    LONG_CONTEXT = "long_context"


class RoutingContext(BaseModel):
    """
    路由输入：Prompt、显式 Task、成本/延迟偏好。
    """

    prompt: str = ""
    task: TaskKind | str | None = None
    prefer_low_cost: bool = False
    prefer_low_latency: bool = False
    max_cost_per_1m: float | None = None
    min_context_length: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoredCandidate(BaseModel):
    """候选模型得分明细。"""

    model_name: str
    model_id: str
    cost_score: float
    latency_score: float
    preference_score: float
    composite_score: float
    estimated_latency_ms: float
    blended_cost_per_1m: float


class RoutingReport(BaseModel):
    """
    路由决策报告（可写入 Trace / 日志 / API 响应）。
    """

    task_type: TaskKind
    policy_name: str
    selected_model: ModelInfo
    selected_registry_name: str
    reasons: list[str] = Field(default_factory=list)
    prompt_signals: dict[str, Any] = Field(default_factory=dict)
    cost_weight: float = 0.0
    latency_weight: float = 0.0
    preference_weight: float = 0.0
    winner: ScoredCandidate | None = None
    candidates: list[ScoredCandidate] = Field(default_factory=list)

    def summary(self) -> str:
        return (
            f"task={self.task_type.value} policy={self.policy_name} "
            f"model={self.selected_registry_name} "
            f"({self.selected_model.model_id})"
        )
