"""AI Infra Dashboard 数据模型（Task 7.8）。"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class ModelInfraStatus(BaseModel):
    registry_name: str
    model_id: str
    provider: str
    status: str = "registered"
    qps: float = 0.0
    latency_avg_ms: float = 0.0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    requests_total: int = 0


class GpuDashboardView(BaseModel):
    index: int = 0
    utilization_percent: float | None = None
    memory_used_mib: float | None = None
    memory_total_mib: float | None = None
    temperature_c: float | None = None


class CacheDashboardView(BaseModel):
    backend: str = "memory"
    layers: dict[str, dict[str, float | int]] = Field(default_factory=dict)


class AgentRuntimeDashboardView(BaseModel):
    scheduler: dict[str, Any] = Field(default_factory=dict)
    registered_agents: list[str] = Field(default_factory=list)


class GatewayTokensView(BaseModel):
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    by_backend: dict[str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)


class InfraDashboardOverview(BaseModel):
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    models: list[ModelInfraStatus] = Field(default_factory=list)
    http_qps_estimate: float = 0.0
    http_latency_avg_ms: float = 0.0
    http_error_rate: float = 0.0
    http_requests_total: int = 0
    gateway_tokens: GatewayTokensView = Field(
        default_factory=GatewayTokensView,
    )
    gpu: list[GpuDashboardView] = Field(default_factory=list)
    gpu_report_summary: dict[str, Any] = Field(default_factory=dict)
    cache: CacheDashboardView = Field(default_factory=CacheDashboardView)
    service_discovery: dict[str, Any] = Field(default_factory=dict)
    agents: AgentRuntimeDashboardView = Field(
        default_factory=AgentRuntimeDashboardView,
    )
