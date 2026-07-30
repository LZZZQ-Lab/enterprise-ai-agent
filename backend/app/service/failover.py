"""
Failover：健康节点选择与故障切换。
"""

from __future__ import annotations

import threading

from app.service.registry import ProviderRegistry
from app.service.types import FailoverEvent
from app.service.types import ProviderHealth
from app.service.types import ProviderKind
from app.service.types import ProviderNode


class FailoverSelector:
    """
    按权重 + 轮询选择健康节点；失败时切换下一节点。
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry
        self._lock = threading.RLock()
        self._round_robin: dict[ProviderKind, int] = {}
        self._active: dict[ProviderKind, str | None] = {
            ProviderKind.VLLM: None,
            ProviderKind.SGLANG: None,
        }
        self._failover_log: list[FailoverEvent] = []

    def select(self, kind: ProviderKind) -> ProviderNode | None:
        candidates = self._registry.list_nodes(
            kind=kind,
            healthy_only=True,
        )
        if not candidates:
            return None

        with self._lock:
            index = self._round_robin.get(kind, 0) % len(candidates)
            self._round_robin[kind] = index + 1
            chosen = candidates[index]
            self._active[kind] = chosen.node_id

        return chosen

    def report_failure(
        self,
        node_id: str,
        *,
        reason: str = "request failed",
    ) -> ProviderNode | None:
        node = self._registry.get(node_id)
        self._registry.mark_health(node_id, healthy=False, error=reason)

        event = FailoverEvent(
            kind=node.kind,
            from_node_id=node_id,
            reason=reason,
        )

        replacement = self.select(node.kind)
        event.to_node_id = replacement.node_id if replacement else None

        with self._lock:
            self._failover_log.append(event)
            if len(self._failover_log) > 100:
                self._failover_log = self._failover_log[-100:]

        return replacement

    def active_node_id(self, kind: ProviderKind) -> str | None:
        with self._lock:
            return self._active.get(kind)

    def recent_failovers(self, limit: int = 20) -> list[FailoverEvent]:
        with self._lock:
            return list(self._failover_log[-limit:])

    def ensure_active(self, kind: ProviderKind) -> ProviderNode | None:
        active_id = self.active_node_id(kind)
        if active_id:
            stored = self._registry.get(active_id)
            if stored.status == ProviderHealth.HEALTHY:
                return stored

        return self.select(kind)
