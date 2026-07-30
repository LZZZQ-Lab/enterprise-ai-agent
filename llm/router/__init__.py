"""
Model Router & Registry（Task 9.1 canonical import）。

Implementation: ``backend/app/router/`` · ``backend/app/model_registry/``
"""

from app.model_registry import *  # noqa: F403
from app.router import *  # noqa: F403

from app.model_registry import __all__ as _registry_all
from app.router import __all__ as _router_all

__all__ = list(dict.fromkeys([*_router_all, *_registry_all]))
