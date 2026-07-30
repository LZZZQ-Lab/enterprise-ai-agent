"""
模型缓存类型（Task 7.6）。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class CacheLayer(str, Enum):
    PROMPT = "prompt"
    EMBEDDING = "embedding"
    RESPONSE = "response"


class CacheBackendKind(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"


class LayerStats(BaseModel):
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total <= 0:
            return 0.0
        return round(self.hits / self.total, 4)


class CacheStatsSnapshot(BaseModel):
    backend: str = "memory"
    layers: dict[str, LayerStats] = Field(default_factory=dict)

    def layer(self, name: CacheLayer | str) -> LayerStats:
        key = name.value if isinstance(name, CacheLayer) else str(name)
        if key not in self.layers:
            self.layers[key] = LayerStats()
        return self.layers[key]

    def summary(self) -> dict[str, dict[str, float | int]]:
        return {
            key: {
                "hits": stats.hits,
                "misses": stats.misses,
                "sets": stats.sets,
                "hit_rate": stats.hit_rate,
            }
            for key, stats in self.layers.items()
        }
