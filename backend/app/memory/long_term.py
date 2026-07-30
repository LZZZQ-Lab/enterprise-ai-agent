"""
Knowledge Memory — 长期知识记忆（Task 6.7）。
"""

from __future__ import annotations

import threading
import time

from app.memory.types import MemoryKind
from app.memory.types import MemoryRecord


class KnowledgeMemory:
    """
    组织 / 项目级长期知识（可对接向量库；当前为内存实现）。
    """

    def __init__(self) -> None:
        self._entries: dict[str, list[MemoryRecord]] = {}
        self._lock = threading.RLock()

    def append(
        self,
        scope_id: str,
        *,
        content: str,
        source: str = "",
        tags: list[str] | None = None,
    ) -> None:
        record = MemoryRecord(
            role="knowledge",
            content=content,
            metadata={
                "memory_kind": MemoryKind.KNOWLEDGE.value,
                "source": source,
                "tags": list(tags or []),
                "timestamp": time.time(),
            },
        )

        with self._lock:
            self._entries.setdefault(scope_id, []).append(record)

    def load(self, scope_id: str, *, limit: int = 50) -> list[MemoryRecord]:
        with self._lock:
            items = list(self._entries.get(scope_id, []))

        return items[-limit:]

    def clear(self, scope_id: str) -> None:
        with self._lock:
            self._entries.pop(scope_id, None)
