"""
聚合 Phase 7 各模块指标，供 Dashboard 展示。
"""

from __future__ import annotations

from app.agents.registry import registry as agent_registry
from app.agents.runtime import default_runtime
from app.cache.stats import get_cache_stats
from app.dashboard.schemas import AgentRuntimeDashboardView
from app.dashboard.schemas import CacheDashboardView
from app.dashboard.schemas import GpuDashboardView
from app.dashboard.schemas import GatewayTokensView
from app.dashboard.schemas import InfraDashboardOverview
from app.dashboard.schemas import ModelInfraStatus
from app.gateway.stats import get_token_stats
from app.gpu.manager import get_gpu_resource_manager
from app.model_registry.manager import get_model_registry_manager
from app.monitoring.metrics import infra_metrics
from app.service.manager import get_service_discovery_manager


class InfraDashboardCollector:
    def collect(self) -> InfraDashboardOverview:
        metrics = infra_metrics.summarize()
        gateway = get_token_stats()
        cache_stats = get_cache_stats()
        gpu_report = get_gpu_resource_manager().build_status_report()
        discovery = get_service_discovery_manager().build_report()

        models = self._build_models(metrics, gateway)
        gpu_views = self._build_gpu(metrics, gpu_report)
        cache_view = CacheDashboardView(
            backend=cache_stats.backend,
            layers=cache_stats.summary(),
        )

        agents_view = self._build_agents()

        return InfraDashboardOverview(
            models=models,
            http_qps_estimate=float(metrics.get("http_qps_estimate", 0.0)),
            http_latency_avg_ms=float(
                metrics.get("http_latency_avg_ms", 0.0),
            ),
            http_error_rate=float(metrics.get("http_error_rate", 0.0)),
            http_requests_total=int(metrics.get("http_requests_total", 0)),
            gateway_tokens=GatewayTokensView(
                total_requests=gateway.total_requests,
                prompt_tokens=gateway.prompt_tokens,
                completion_tokens=gateway.completion_tokens,
                total_tokens=gateway.total_tokens,
                by_backend=dict(gateway.by_backend),
                by_model=dict(gateway.by_model),
            ),
            gpu=gpu_views,
            gpu_report_summary=gpu_report.summary,
            cache=cache_view,
            service_discovery={
                "active_by_kind": discovery.active_by_kind,
                "provider_count": len(discovery.providers),
                "recent_failovers": [
                    item.model_dump()
                    for item in discovery.recent_failovers[:5]
                ],
            },
            agents=agents_view,
        )

    def _build_models(
        self,
        metrics: dict[str, object],
        gateway,
    ) -> list[ModelInfraStatus]:
        llm_by_model = metrics.get("llm_by_model") or {}
        if not isinstance(llm_by_model, dict):
            llm_by_model = {}

        registry = get_model_registry_manager()
        items: list[ModelInfraStatus] = []

        for info in registry.list_models():
            stats = llm_by_model.get(info.model_id, {})
            if not isinstance(stats, dict):
                stats = llm_by_model.get(info.name, {})
            if not isinstance(stats, dict):
                stats = {}

            requests = int(stats.get("requests", 0))
            latency = float(stats.get("latency_avg_ms", 0.0))
            qps = 0.0
            if latency > 0 and requests > 0:
                qps = round(1000.0 / latency, 2)

            gateway_hits = gateway.by_model.get(info.model_id, 0)
            status = "active" if requests or gateway_hits else "idle"

            items.append(
                ModelInfraStatus(
                    registry_name=info.name,
                    model_id=info.model_id,
                    provider=info.provider.value,
                    status=status,
                    qps=qps,
                    latency_avg_ms=latency,
                    tokens_prompt=int(stats.get("tokens_prompt", 0)),
                    tokens_completion=int(
                        stats.get("tokens_completion", 0),
                    ),
                    requests_total=requests,
                ),
            )

        return items

    def _build_gpu(
        self,
        metrics: dict[str, object],
        gpu_report,
    ) -> list[GpuDashboardView]:
        devices = metrics.get("gpu_devices") or []
        if isinstance(devices, list) and devices:
            return [
                GpuDashboardView(
                    index=int(item.get("index", 0)),
                    utilization_percent=_float_or_none(
                        item.get("utilization_percent"),
                    ),
                    memory_used_mib=_float_or_none(
                        item.get("memory_used_mib"),
                    ),
                    memory_total_mib=_float_or_none(
                        item.get("memory_total_mib"),
                    ),
                    temperature_c=_float_or_none(
                        item.get("temperature_c"),
                    ),
                )
                for item in devices
                if isinstance(item, dict)
            ]

        return [
            GpuDashboardView(
                index=dev.index,
                utilization_percent=dev.utilization_percent,
                memory_used_mib=dev.memory_used_mib,
                memory_total_mib=dev.memory_total_mib,
                temperature_c=dev.temperature_c,
            )
            for dev in gpu_report.devices
        ]

    def _build_agents(self) -> AgentRuntimeDashboardView:
        scheduler_stats: dict[str, object] = {}
        scheduler = getattr(default_runtime, "_scheduler", None)
        if scheduler is not None:
            scheduler_stats = scheduler.dashboard_snapshot()

        return AgentRuntimeDashboardView(
            scheduler=scheduler_stats,
            registered_agents=sorted(
                agent_registry.list_agents(),
            ),
        )


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
