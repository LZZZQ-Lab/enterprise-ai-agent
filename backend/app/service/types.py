"""
服务发现类型（Task 7.5）。
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class ProviderKind(str, Enum):
    VLLM = "vllm"
    SGLANG = "sglang"


class ProviderHealth(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STALE = "stale"


class ProviderNode(BaseModel):
    """推理节点注册信息。"""

    node_id: str
    kind: ProviderKind
    base_url: str
    api_key: str = "EMPTY"
    weight: int = Field(default=100, ge=1)
    status: ProviderHealth = ProviderHealth.UNKNOWN
    last_heartbeat_at: datetime | None = None
    last_health_check_at: datetime | None = None
    last_error: str = ""
    failure_count: int = 0
    success_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def origin(self) -> str:
        url = self.base_url.rstrip("/")
        if url.endswith("/v1"):
            return url[:-3]
        return url


class HeartbeatRequest(BaseModel):
    node_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderRegisterRequest(BaseModel):
    node_id: str | None = None
    kind: ProviderKind
    base_url: str
    api_key: str = "EMPTY"
    weight: int = 100
    metadata: dict[str, Any] = Field(default_factory=dict)


class FailoverEvent(BaseModel):
    kind: ProviderKind
    from_node_id: str | None = None
    to_node_id: str | None = None
    reason: str = ""


class ServiceDiscoveryReport(BaseModel):
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    providers: list[ProviderNode] = Field(default_factory=list)
    active_by_kind: dict[str, str | None] = Field(default_factory=dict)
    recent_failovers: list[FailoverEvent] = Field(default_factory=list)
