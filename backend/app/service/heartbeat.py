"""
Heartbeat 与节点过期检测。
"""

from __future__ import annotations

import threading
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.service.registry import ProviderRegistry
from app.service.types import ProviderHealth
from app.service.types import ProviderNode


class HeartbeatMonitor:
    """
    记录心跳并将超时节点标记为 STALE。
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        stale_after_seconds: float = 45.0,
    ) -> None:
        self._registry = registry
        self._stale_after = stale_after_seconds
        self._lock = threading.RLock()

    def record(self, node_id: str) -> ProviderNode:
        return self._registry.touch_heartbeat(node_id)

    def mark_stale_nodes(self) -> list[str]:
        now = datetime.now(timezone.utc)
        stale_ids: list[str] = []

        for node in self._registry.list_nodes():
            if node.last_heartbeat_at is None:
                continue
            age = now - node.last_heartbeat_at
            if age > timedelta(seconds=self._stale_after):
                self._registry.mark_stale(node.node_id)
                stale_ids.append(node.node_id)

        return stale_ids
