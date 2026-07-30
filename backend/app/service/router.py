"""
服务发现 REST API。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException

from app.service.manager import get_service_discovery_manager
from app.service.types import HeartbeatRequest
from app.service.types import ProviderNode
from app.service.types import ProviderRegisterRequest
from app.service.types import ServiceDiscoveryReport

router = APIRouter(prefix="/service", tags=["Service Discovery"])


@router.get("/providers", response_model=list[ProviderNode])
def list_providers() -> list[ProviderNode]:
    return get_service_discovery_manager().registry.list_nodes()


@router.post("/providers/register", response_model=ProviderNode)
def register_provider(body: ProviderRegisterRequest) -> ProviderNode:
    return get_service_discovery_manager().register(body)


@router.delete("/providers/{node_id}")
def unregister_provider(node_id: str) -> dict[str, bool]:
    removed = get_service_discovery_manager().registry.unregister(node_id)
    if not removed:
        raise HTTPException(status_code=404, detail="node not found")
    return {"removed": True}


@router.post("/heartbeat", response_model=ProviderNode)
def provider_heartbeat(body: HeartbeatRequest) -> ProviderNode:
    try:
        return get_service_discovery_manager().heartbeat(body.node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/health/check")
def run_health_checks() -> dict[str, bool]:
    return get_service_discovery_manager().run_health_checks()


@router.get("/report", response_model=ServiceDiscoveryReport)
def service_discovery_report() -> ServiceDiscoveryReport:
    return get_service_discovery_manager().build_report()
