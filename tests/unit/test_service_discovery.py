"""Task 7.5 Service Discovery 测试。"""

from __future__ import annotations

from unittest.mock import patch

from app.service.discovery import bootstrap_providers
from app.service.failover import FailoverSelector
from app.service.health import HealthChecker
from app.service.manager import ServiceDiscoveryManager
from app.service.registry import ProviderRegistry
from app.service.types import ProviderHealth
from app.service.types import ProviderKind
from app.service.types import ProviderNode
from app.service.types import ProviderRegisterRequest


def test_registry_and_bootstrap() -> None:
    registry = ProviderRegistry()

    class FakeSettings:
        VLLM_NODES = "http://127.0.0.1:8000/v1,http://127.0.0.1:8002/v1"
        SGLANG_NODES = ""
        VLLM_ENDPOINT = "http://127.0.0.1:8000/v1"
        SGLANG_ENDPOINT = "http://127.0.0.1:30000/v1"
        VLLM_API_KEY = "EMPTY"
        SGLANG_API_KEY = "EMPTY"
        API_KEY = ""

    count = bootstrap_providers(registry, FakeSettings(), overwrite=True)
    assert count >= 2
    nodes = registry.list_nodes(kind=ProviderKind.VLLM)
    assert len(nodes) >= 2


def test_health_checker_success() -> None:
    checker = HealthChecker(timeout_seconds=1.0)
    node = ProviderNode(
        node_id="v1",
        kind=ProviderKind.VLLM,
        base_url="http://127.0.0.1:8000/v1",
    )

    with patch.object(
        checker,
        "_probe_url",
        side_effect=[(True, ""), (False, "skip")],
    ):
        ok, err = checker.check(node)

    assert ok is True
    assert err == ""


def test_failover_switches_node() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderRegisterRequest(
            node_id="a",
            kind=ProviderKind.VLLM,
            base_url="http://a/v1",
        ),
        overwrite=True,
    )
    registry.register(
        ProviderRegisterRequest(
            node_id="b",
            kind=ProviderKind.VLLM,
            base_url="http://b/v1",
        ),
        overwrite=True,
    )
    registry.mark_health("a", healthy=True)
    registry.mark_health("b", healthy=True)

    selector = FailoverSelector(registry)
    first = selector.select(ProviderKind.VLLM)
    assert first is not None

    replacement = selector.report_failure("a", reason="timeout")
    assert replacement is not None
    assert replacement.node_id != "a"
    assert selector.recent_failovers()


def test_manager_resolve_after_health(monkeypatch) -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderRegisterRequest(
            node_id="vllm-1",
            kind=ProviderKind.VLLM,
            base_url="http://127.0.0.1:8010/v1",
        ),
        overwrite=True,
    )

    manager = ServiceDiscoveryManager(registry=registry, auto_bootstrap=False)

    monkeypatch.setenv("ENABLE_SERVICE_DISCOVERY", "true")
    from app.config.settings import get_settings

    get_settings.cache_clear()

    with patch.object(
        manager.health,
        "check",
        return_value=(True, ""),
    ):
        node = manager.resolve_node(ProviderKind.VLLM)

    assert node is not None
    assert node.node_id == "vllm-1"
    assert node.status == ProviderHealth.HEALTHY


def test_heartbeat_marks_stale() -> None:
    from datetime import datetime
    from datetime import timedelta
    from datetime import timezone

    registry = ProviderRegistry()
    node = registry.register(
        ProviderRegisterRequest(
            node_id="hb",
            kind=ProviderKind.SGLANG,
            base_url="http://sglang/v1",
        ),
        overwrite=True,
    )

    with registry._lock:
        stored = registry._nodes[node.node_id]
        stored.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(
            seconds=120,
        )

    manager = ServiceDiscoveryManager(registry=registry, auto_bootstrap=False)
    stale = manager.heartbeat.mark_stale_nodes()
    assert "hb" in stale
