"""
Redis TTL 缓存（REDIS_URL 未配置时由工厂回退 Memory）。
"""

from __future__ import annotations

from app.cache.base import CacheStore


class RedisCacheStore(CacheStore):
    def __init__(
        self,
        redis_url: str,
        *,
        key_prefix: str = "enterprise_ai:",
    ) -> None:
        import redis

        self._client = redis.from_url(
            redis_url,
            decode_responses=False,
        )
        self._prefix = key_prefix

    @property
    def backend_name(self) -> str:
        return "redis"

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> bytes | None:
        value = self._client.get(self._full_key(key))
        if value is None:
            return None
        if isinstance(value, str):
            return value.encode("utf-8")
        return value

    def set(
        self,
        key: str,
        value: bytes,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        full = self._full_key(key)
        if ttl_seconds is not None and ttl_seconds > 0:
            self._client.setex(full, ttl_seconds, value)
        else:
            self._client.set(full, value)

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(self._full_key(key)))

    def clear(self) -> int:
        count = 0
        pattern = f"{self._prefix}model_cache:*"
        cursor = 0
        while True:
            cursor, keys = self._client.scan(
                cursor=cursor,
                match=pattern,
                count=200,
            )
            if keys:
                count += int(self._client.delete(*keys))
            if cursor == 0:
                break
        return count
