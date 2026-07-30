"""
Conversation Memory — 会话级短期记忆（Task 6.7）。
"""

from __future__ import annotations

from app.memory.inmemory import InMemory
from app.memory.types import MemoryContext
from app.memory.types import MemoryKind
from app.memory.types import MemoryRecord


class ShortTermMemory:
    """
    按 session_id 存储对话轮次。
    """

    def __init__(self) -> None:
        self._store = InMemory()

    def load(self, session_id: str) -> MemoryContext:
        ctx = self._store.load(session_id)

        for record in ctx.records:
            record.metadata.setdefault("memory_kind", MemoryKind.CONVERSATION.value)

        return ctx

    def append(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        meta = dict(metadata or {})
        meta["memory_kind"] = MemoryKind.CONVERSATION.value

        self._store.save(
            session_id,
            MemoryRecord(role=role, content=content, metadata=meta),
        )

    def save_record(self, session_id: str, record: MemoryRecord) -> None:
        record.metadata.setdefault("memory_kind", MemoryKind.CONVERSATION.value)
        self._store.save(session_id, record)

    def clear(self, session_id: str) -> None:
        self._store.clear(session_id)
