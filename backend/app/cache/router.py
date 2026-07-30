"""
Model Cache REST API。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.cache.manager import get_model_cache_manager
from app.cache.stats import get_cache_stats
from app.cache.stats import reset_cache_stats
from app.cache.types import CacheStatsSnapshot

router = APIRouter(prefix="/cache", tags=["Model Cache"])


@router.get("/stats", response_model=CacheStatsSnapshot)
def cache_stats() -> CacheStatsSnapshot:
    return get_cache_stats()


@router.post("/clear")
def clear_cache() -> dict[str, int | str]:
    removed = get_model_cache_manager().clear_all()
    reset_cache_stats()
    return {"cleared": removed, "status": "ok"}
