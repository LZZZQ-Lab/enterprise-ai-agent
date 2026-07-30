"""
Model Cache 管理器与 Store 工厂。
"""

from __future__ import annotations

import threading

from app.cache.base import CacheStore
from app.cache.layers import EmbeddingCache
from app.cache.layers import PromptCache
from app.cache.layers import ResponseCache
from app.cache.memory import MemoryCacheStore
from app.cache.stats import set_backend_label
from app.cache.types import CacheBackendKind

_manager_lock = threading.Lock()
_default_manager: ModelCacheManager | None = None


class ModelCacheManager:
    def __init__(self, store: CacheStore | None = None) -> None:
        self.store = store or create_cache_store()
        set_backend_label(self.store.backend_name)

        settings = _cache_settings()
        self.prompt = PromptCache(
            self.store,
            ttl_seconds=settings["prompt_ttl"],
        )
        self.embedding_template = EmbeddingCache(
            self.store,
            ttl_seconds=settings["embedding_ttl"],
        )
        self.response = ResponseCache(
            self.store,
            ttl_seconds=settings["response_ttl"],
        )

    def embedding_for(
        self,
        *,
        model: str,
        dimension: int,
    ) -> EmbeddingCache:
        return EmbeddingCache(
            self.store,
            ttl_seconds=_cache_settings()["embedding_ttl"],
            model=model,
            dimension=dimension,
        )

    def clear_all(self) -> int:
        return self.store.clear()


def create_cache_store() -> CacheStore:
    settings = _cache_settings()
    if (
        settings["backend"] == CacheBackendKind.REDIS.value
        and settings["redis_url"]
    ):
        try:
            from app.cache.redis_store import RedisCacheStore

            return RedisCacheStore(settings["redis_url"])
        except Exception:
            pass

    return MemoryCacheStore(max_entries=settings["memory_max_entries"])


def get_model_cache_manager() -> ModelCacheManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = ModelCacheManager()
        return _default_manager


def reset_model_cache_manager() -> None:
    global _default_manager

    with _manager_lock:
        _default_manager = None


def cache_enabled() -> bool:
    try:
        from app.config.settings import get_settings

        return get_settings().ENABLE_MODEL_CACHE
    except Exception:
        return False


def _cache_settings() -> dict:
    from app.config.settings import get_settings

    app = get_settings()
    backend = (app.CACHE_BACKEND or "memory").strip().lower()
    return {
        "backend": backend,
        "redis_url": app.REDIS_URL.strip(),
        "prompt_ttl": app.CACHE_PROMPT_TTL_SEC,
        "embedding_ttl": app.CACHE_EMBEDDING_TTL_SEC,
        "response_ttl": app.CACHE_RESPONSE_TTL_SEC,
        "memory_max_entries": app.CACHE_MEMORY_MAX_ENTRIES,
    }
