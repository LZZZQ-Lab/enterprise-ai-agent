"""
缓存存储抽象。
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class CacheStore(ABC):
    @abstractmethod
    def get(self, key: str) -> bytes | None:
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: bytes,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def clear(self) -> int:
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        pass
