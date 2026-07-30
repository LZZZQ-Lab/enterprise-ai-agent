"""
Provider Registry：推理节点注册表。
"""

from __future__ import annotations

import threading
import uuid

from app.service.types import ProviderHealth
from app.service.types import ProviderKind
from app.service.types import ProviderNode
from app.service.types import ProviderRegisterRequest


class ProviderRegistry:
    """
    内存 Provider 注册中心（vLLM / SGLang 等多节点）。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nodes: dict[str, ProviderNode] = {}

    def register(
        self,
        request: ProviderRegisterRequest,
        *,
        overwrite: bool = False,
    ) -> ProviderNode:
        with self._lock:
            node_id = request.node_id or uuid.uuid4().hex
            if node_id in self._nodes and not overwrite:
                raise ValueError(f"Provider node '{node_id}' already exists")

            node = ProviderNode(
                node_id=node_id,
                kind=request.kind,
                base_url=_normalize_base_url(request.base_url),
                api_key=request.api_key or "EMPTY",
                weight=request.weight,
                metadata=dict(request.metadata),
                status=ProviderHealth.UNKNOWN,
            )
            self._nodes[node_id] = node
            return node.model_copy(deep=True)

    def unregister(self, node_id: str) -> bool:
        with self._lock:
            return self._nodes.pop(node_id, None) is not None

    def get(self, node_id: str) -> ProviderNode:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(f"Unknown provider node: {node_id}")
            return node.model_copy(deep=True)

    def list_nodes(
        self,
        *,
        kind: ProviderKind | None = None,
        healthy_only: bool = False,
    ) -> list[ProviderNode]:
        with self._lock:
            items = list(self._nodes.values())

        if kind is not None:
            items = [node for node in items if node.kind == kind]

        if healthy_only:
            items = [
                node
                for node in items
                if node.status == ProviderHealth.HEALTHY
            ]

        return sorted(
            [node.model_copy(deep=True) for node in items],
            key=lambda node: (node.kind.value, node.node_id),
        )

    def upsert_node(self, node: ProviderNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def touch_heartbeat(self, node_id: str) -> ProviderNode:
        from datetime import datetime
        from datetime import timezone

        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(f"Unknown provider node: {node_id}")
            node.last_heartbeat_at = datetime.now(timezone.utc)
            if node.status in {
                ProviderHealth.UNKNOWN,
                ProviderHealth.STALE,
            }:
                node.status = ProviderHealth.HEALTHY
            self._nodes[node_id] = node
            return node.model_copy(deep=True)

    def mark_health(
        self,
        node_id: str,
        *,
        healthy: bool,
        error: str = "",
    ) -> None:
        from datetime import datetime
        from datetime import timezone

        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return

            node.last_health_check_at = datetime.now(timezone.utc)
            if healthy:
                node.status = ProviderHealth.HEALTHY
                node.success_count += 1
                node.failure_count = 0
                node.last_error = ""
            else:
                node.status = ProviderHealth.UNHEALTHY
                node.failure_count += 1
                node.last_error = error
            self._nodes[node_id] = node

    def mark_stale(self, node_id: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return
            node.status = ProviderHealth.STALE
            node.last_error = "heartbeat stale"
            self._nodes[node_id] = node


def _normalize_base_url(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise ValueError("base_url must not be empty")
    if not cleaned.endswith("/v1"):
        cleaned = f"{cleaned}/v1"
    return cleaned
