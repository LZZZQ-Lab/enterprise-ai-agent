"""
FastAPI 应用入口（Task 9.1）。

Canonical::

    from apps.api import app
    uvicorn apps.api:app --host 0.0.0.0 --port 8001

兼容::

    uvicorn app.main:app
"""

from app.main import app

__all__ = ["app"]
