"""
缓存命中率统计。
"""

from __future__ import annotations

import threading

from app.cache.types import CacheLayer
from app.cache.types import CacheStatsSnapshot
from app.cache.types import LayerStats

_lock = threading.Lock()
_stats = CacheStatsSnapshot()
_backend_label = "memory"


def set_backend_label(label: str) -> None:
    global _backend_label

    with _lock:
        _backend_label = label
        _stats.backend = label


def record_hit(layer: CacheLayer) -> None:
    with _lock:
        _stats.layer(layer).hits += 1


def record_miss(layer: CacheLayer) -> None:
    with _lock:
        _stats.layer(layer).misses += 1


def record_set(layer: CacheLayer) -> None:
    with _lock:
        _stats.layer(layer).sets += 1


def record_eviction(layer: CacheLayer, count: int = 1) -> None:
    with _lock:
        _stats.layer(layer).evictions += count


def get_cache_stats() -> CacheStatsSnapshot:
    with _lock:
        return _stats.model_copy(deep=True)


def reset_cache_stats() -> None:
    global _stats

    with _lock:
        _stats = CacheStatsSnapshot(backend=_backend_label)
