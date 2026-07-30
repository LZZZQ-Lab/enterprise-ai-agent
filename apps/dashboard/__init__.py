"""
Dashboard API 与 Demo 页面（Task 9.1）。

Canonical::

    from apps.dashboard import api_router, demo_router
"""

from app.dashboard.router import api_router
from app.dashboard.router import demo_router
from app.dashboard.collector import InfraDashboardCollector
from app.dashboard.schemas import InfraDashboardOverview

__all__ = [
    "InfraDashboardCollector",
    "InfraDashboardOverview",
    "api_router",
    "demo_router",
]
