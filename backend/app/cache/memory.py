"""
进程内 TTL 缓存。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.cache.base import CacheStore


@dataclass
class _Entry:
    value: bytes
    expires_at: float | None


class MemoryCacheStore(CacheStore):
    def __init__(self, *, max_entries: int = 10_000) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, _Entry] = {}
        self._max_entries = max_entries

    @property
    def backend_name(self) -> str:
        return "memory"

    def get(self, key: str) -> bytes | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.expires_at is not None and time.time() > entry.expires_at:
                self._data.pop(key, None)
                return None
            return entry.value

    def set(
        self,
        key: str,
        value: bytes,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        expires = None
        if ttl_seconds is not None and ttl_seconds > 0:
            expires = time.time() + ttl_seconds

        with self._lock:
            if len(self._data) >= self._max_entries and key not in self._data:
                self._evict_one()
            self._data[key] = _Entry(value=value, expires_at=expires)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def clear(self) -> int:
        with self._lock:
            count = len(self._data)
            self._data.clear()
            return count

    def _evict_one(self) -> None:
        if not self._data:
            return
        oldest_key = next(iter(self._data))
        self._data.pop(oldest_key, None)
