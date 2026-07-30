"""
Task 7.2 Model Router — 按任务自动选择模型。
"""

from app.router.engine import RouterEngine
from app.router.engine import get_router_engine
from app.router.engine import reset_router_engine
from app.router.policy import DEFAULT_ROUTE_POLICIES
from app.router.policy import RoutePolicy
from app.router.types import RoutingContext
from app.router.types import RoutingReport
from app.router.types import TaskKind

__all__ = [
    "DEFAULT_ROUTE_POLICIES",
    "RoutePolicy",
    "RouterEngine",
    "RoutingContext",
    "RoutingReport",
    "TaskKind",
    "get_router_engine",
    "reset_router_engine",
]
