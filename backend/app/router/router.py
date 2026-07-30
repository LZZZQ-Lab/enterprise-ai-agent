"""
Model Router API — 返回 Routing Report。
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from pydantic import Field

from app.router.engine import get_router_engine
from app.router.types import RoutingContext
from app.router.types import RoutingReport
from app.router.types import TaskKind

router = APIRouter(prefix="/router", tags=["Model Router"])


class RouteRequest(BaseModel):
    prompt: str = ""
    task: TaskKind | None = None
    prefer_low_cost: bool = False
    prefer_low_latency: bool = False
    max_cost_per_1m: float | None = None
    min_context_length: int | None = None
    metadata: dict = Field(default_factory=dict)


@router.post("/route", response_model=RoutingReport)
def route_model(body: RouteRequest) -> RoutingReport:
    engine = get_router_engine()
    context = RoutingContext(
        prompt=body.prompt,
        task=body.task,
        prefer_low_cost=body.prefer_low_cost,
        prefer_low_latency=body.prefer_low_latency,
        max_cost_per_1m=body.max_cost_per_1m,
        min_context_length=body.min_context_length,
        metadata=dict(body.metadata),
    )
    return engine.route(context)
