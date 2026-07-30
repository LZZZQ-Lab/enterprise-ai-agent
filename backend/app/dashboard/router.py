"""
AI Infra Dashboard REST 与 Demo 页面（Task 7.8）。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.dashboard.collector import InfraDashboardCollector
from app.dashboard.demo_html import DEMO_HTML
from app.dashboard.schemas import InfraDashboardOverview

api_router = APIRouter(
    prefix="/infra/dashboard",
    tags=["AI Infra Dashboard"],
)

demo_router = APIRouter(tags=["AI Infra Dashboard"])

_collector = InfraDashboardCollector()


@api_router.get("/overview", response_model=InfraDashboardOverview)
def infra_dashboard_overview() -> InfraDashboardOverview:
    """聚合模型、Gateway、GPU、缓存、服务发现与 Agent 调度指标。"""
    return _collector.collect()


@demo_router.get(
    "/infra/dashboard/demo",
    response_class=HTMLResponse,
    include_in_schema=True,
)
def infra_dashboard_demo() -> HTMLResponse:
    """Dashboard Demo：浏览器打开即可轮询 overview API。"""
    return HTMLResponse(content=DEMO_HTML)
