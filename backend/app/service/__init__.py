"""
Task 7.5 Service Discovery。
"""

from app.service.manager import ServiceDiscoveryManager
from app.service.manager import get_service_discovery_manager
from app.service.manager import reset_service_discovery_manager
from app.service.registry import ProviderRegistry
from app.service.types import ProviderKind
from app.service.types import ProviderNode
from app.service.types import ServiceDiscoveryReport

__all__ = [
    "ProviderKind",
    "ProviderNode",
    "ProviderRegistry",
    "ServiceDiscoveryManager",
    "ServiceDiscoveryReport",
    "get_service_discovery_manager",
    "reset_service_discovery_manager",
]
