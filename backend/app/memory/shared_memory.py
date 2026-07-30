"""
Project Memory 与 Shared Memory — 跨 Agent 共享（Task 6.7）。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from dataclasses import field

from app.memory.types import MemoryKind
from app.memory.types import MemoryRecord


@dataclass
class ProjectMemoryEntry:
    key: str
    value: str
    agent_name: str = ""
    updated_at: float = field(default_factory=time.time)


class ProjectMemory:
    """
    项目级 Memory：Manager / Developer 等 Agent 读写同一 project_id。
    """

    def __init__(self) -> None:
        self._projects: dict[str, dict[str, ProjectMemoryEntry]] = {}
        self._lock = threading.RLock()

    def put(
        self,
        project_id: str,
        key: str,
        value: str,
        *,
        agent_name: str = "",
    ) -> None:
        with self._lock:
            bucket = self._projects.setdefault(project_id, {})
            bucket[key] = ProjectMemoryEntry(
                key=key,
                value=value,
                agent_name=agent_name,
                updated_at=time.time(),
            )

    def get(self, project_id: str, key: str) -> str | None:
        with self._lock:
            entry = self._projects.get(project_id, {}).get(key)

            if entry is None:
                return None

            return entry.value

    def get_all(self, project_id: str) -> dict[str, str]:
        with self._lock:
            bucket = self._projects.get(project_id, {})
            return {key: entry.value for key, entry in bucket.items()}

    def clear_project(self, project_id: str) -> None:
        with self._lock:
            self._projects.pop(project_id, None)

    def to_records(self, project_id: str) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []

        with self._lock:
            bucket = self._projects.get(project_id, {})

            for entry in bucket.values():
                records.append(
                    MemoryRecord(
                        role="project",
                        content=f"{entry.key}: {entry.value}",
                        metadata={
                            "memory_kind": MemoryKind.PROJECT.value,
                            "project_id": project_id,
                            "key": entry.key,
                            "agent_name": entry.agent_name,
                            "updated_at": entry.updated_at,
                        },
                    )
                )

        return records


class SharedMemory:
    """
    跨 Agent 广播频道（同一 project / session 内共享事件）。
    """

    def __init__(self) -> None:
        self._channels: dict[str, list[MemoryRecord]] = {}
        self._lock = threading.RLock()

    def publish(
        self,
        channel_id: str,
        *,
        agent_name: str,
        content: str,
        message_type: str = "event",
    ) -> None:
        record = MemoryRecord(
            role="shared",
            content=content,
            metadata={
                "memory_kind": MemoryKind.SHARED.value,
                "channel_id": channel_id,
                "agent_name": agent_name,
                "message_type": message_type,
                "timestamp": time.time(),
            },
        )

        with self._lock:
            self._channels.setdefault(channel_id, []).append(record)

    def read(self, channel_id: str, *, limit: int = 100) -> list[MemoryRecord]:
        with self._lock:
            items = list(self._channels.get(channel_id, []))

        return items[-limit:]

    def clear(self, channel_id: str) -> None:
        with self._lock:
            self._channels.pop(channel_id, None)
