"""
Service Discovery 统一管理。
"""

from __future__ import annotations

import threading
from datetime import datetime
from datetime import timezone

from app.config.settings import get_settings
from app.service.discovery import bootstrap_providers
from app.service.failover import FailoverSelector
from app.service.health import HealthChecker
from app.service.heartbeat import HeartbeatMonitor
from app.service.registry import ProviderRegistry
from app.service.types import ProviderKind
from app.service.types import ProviderNode
from app.service.types import ProviderRegisterRequest
from app.service.types import ServiceDiscoveryReport

_manager_lock = threading.Lock()
_default_manager: ServiceDiscoveryManager | None = None


class ServiceDiscoveryManager:
    """
    Provider Registry + Health + Heartbeat + Failover。
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        *,
        auto_bootstrap: bool = True,
    ) -> None:
        self.registry = registry or ProviderRegistry()
        self.health = HealthChecker(
            timeout_seconds=_health_timeout(),
        )
        self.heartbeat = HeartbeatMonitor(
            self.registry,
            stale_after_seconds=_stale_after(),
        )
        self.failover = FailoverSelector(self.registry)

        if auto_bootstrap:
            bootstrap_providers(self.registry, overwrite=True)

    def register(self, request: ProviderRegisterRequest) -> ProviderNode:
        return self.registry.register(request, overwrite=True)

    def heartbeat(self, node_id: str) -> ProviderNode:
        return self.heartbeat.record(node_id)

    def run_health_checks(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        self.heartbeat.mark_stale_nodes()

        for node in self.registry.list_nodes():
            ok, err = self.health.check(node)
            self.registry.mark_health(
                node.node_id,
                healthy=ok,
                error=err,
            )
            results[node.node_id] = ok

        return results

    def resolve_node(self, kind: ProviderKind) -> ProviderNode | None:
        if not _discovery_enabled():
            return None

        self.heartbeat.mark_stale_nodes()
        active = self.failover.ensure_active(kind)
        if active is not None:
            return active

        for node in self.registry.list_nodes(kind=kind):
            ok, err = self.health.check(node)
            self.registry.mark_health(node.node_id, healthy=ok, error=err)
            if ok:
                return self.failover.select(kind)

        return None

    def resolve_base_url(self, kind: ProviderKind) -> str | None:
        node = self.resolve_node(kind)
        if node is None:
            return None
        return node.base_url

    def resolve_api_key(self, kind: ProviderKind) -> str | None:
        node = self.resolve_node(kind)
        if node is None:
            return None
        return node.api_key

    def on_request_failure(
        self,
        node_id: str,
        *,
        reason: str = "inference error",
    ) -> ProviderNode | None:
        return self.failover.report_failure(node_id, reason=reason)

    def build_report(self) -> ServiceDiscoveryReport:
        active = {
            ProviderKind.VLLM.value: self.failover.active_node_id(
                ProviderKind.VLLM,
            ),
            ProviderKind.SGLANG.value: self.failover.active_node_id(
                ProviderKind.SGLANG,
            ),
        }
        return ServiceDiscoveryReport(
            generated_at=datetime.now(timezone.utc),
            providers=self.registry.list_nodes(),
            active_by_kind=active,
            recent_failovers=self.failover.recent_failovers(),
        )


def get_service_discovery_manager() -> ServiceDiscoveryManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = ServiceDiscoveryManager()
        return _default_manager


def reset_service_discovery_manager() -> None:
    global _default_manager

    with _manager_lock:
        _default_manager = None


def _discovery_enabled() -> bool:
    try:
        return get_settings().ENABLE_SERVICE_DISCOVERY
    except Exception:
        return True


def _health_timeout() -> float:
    try:
        return float(get_settings().SERVICE_HEALTH_TIMEOUT_SEC)
    except Exception:
        return 5.0


def _stale_after() -> float:
    try:
        return float(get_settings().SERVICE_STALE_AFTER_SEC)
    except Exception:
        return 45.0
