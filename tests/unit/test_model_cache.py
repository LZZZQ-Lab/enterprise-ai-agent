"""Task 7.6 Model Cache 测试。"""

from __future__ import annotations

import time

from app.cache.layers import EmbeddingCache
from app.cache.layers import ResponseCache
from app.cache.manager import ModelCacheManager
from app.cache.memory import MemoryCacheStore
from app.cache.stats import get_cache_stats
from app.cache.stats import reset_cache_stats
from app.cache.types import CacheLayer
from app.llm.types import ChatResult
from app.llm.types import Message


def test_memory_ttl_expires() -> None:
    store = MemoryCacheStore()
    store.set("k", b"v", ttl_seconds=1)
    assert store.get("k") == b"v"
    time.sleep(1.1)
    assert store.get("k") is None


def test_response_cache_hit_rate() -> None:
    reset_cache_stats()
    store = MemoryCacheStore()
    cache = ResponseCache(store, ttl_seconds=60)
    messages = [Message(role="user", content="hello")]

    assert cache.get(model="m", messages=messages, use_tools=False) is None
    result = ChatResult(model="m", content="world")
    cache.set(model="m", messages=messages, result=result)

    hit = cache.get(model="m", messages=messages, use_tools=False)
    assert hit is not None
    assert hit.content == "world"

    stats = get_cache_stats()
    layer = stats.layer(CacheLayer.RESPONSE)
    assert layer.hits == 1
    assert layer.misses == 1
    assert layer.hit_rate == 0.5


def test_embedding_cache_partial_hits() -> None:
    reset_cache_stats()
    store = MemoryCacheStore()
    cache = EmbeddingCache(
        store,
        ttl_seconds=60,
        model="emb",
        dimension=3,
    )
    cache.set_many(["a"], [[1.0, 2.0, 3.0]])

    values = cache.get_many(["a", "b"])
    assert values[0] == [1.0, 2.0, 3.0]
    assert values[1] is None

    stats = get_cache_stats().layer(CacheLayer.EMBEDDING)
    assert stats.hits == 1
    assert stats.misses == 1


def test_manager_clear() -> None:
    manager = ModelCacheManager(MemoryCacheStore())
    manager.prompt.set(
        model="m",
        messages=[Message(role="user", content="x")],
        payload=[{"role": "user", "content": "x"}],
    )
    assert manager.clear_all() >= 1
