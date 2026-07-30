"""
RouterEngine：结合 Registry、Policy、Cost、Latency 选择模型。
"""

from __future__ import annotations

import threading
from typing import Any

from app.model_registry.manager import ModelRegistryManager
from app.model_registry.manager import get_model_registry_manager
from app.model_registry.models import ModelInfo
from app.router.classifier import resolve_task_kind
from app.router.policy import RoutePolicy
from app.router.policy import build_default_policy_map
from app.router.types import RoutingContext
from app.router.types import RoutingReport
from app.router.types import ScoredCandidate
from app.router.types import TaskKind

_engine_lock = threading.Lock()
_default_engine: RouterEngine | None = None


class RouterEngine:
    """
    根据 Prompt / Task / Cost / Latency 自动路由到 Registry 中的模型。
    """

    def __init__(
        self,
        registry: ModelRegistryManager | None = None,
        policies: dict[TaskKind, RoutePolicy] | None = None,
        *,
        long_context_threshold: int = 6000,
    ) -> None:
        self._registry = registry or get_model_registry_manager()
        self._policies = policies or build_default_policy_map()
        self._long_context_threshold = long_context_threshold

    @property
    def policies(self) -> dict[TaskKind, RoutePolicy]:
        return dict(self._policies)

    def set_policy(self, policy: RoutePolicy) -> None:
        self._policies[policy.task_type] = policy

    def route(self, context: RoutingContext) -> RoutingReport:
        task_kind, signals, task_source = resolve_task_kind(
            context.prompt,
            context.task,
            long_context_threshold=self._long_context_threshold,
        )
        signals["task_source"] = task_source

        policy = self._policies.get(task_kind)
        if policy is None:
            policy = self._policies[TaskKind.CHAT]

        candidates = self._collect_candidates(policy, context, task_kind)
        if not candidates:
            fallback = self._registry.resolve(policy.fallback_model)
            return self._build_report(
                task_kind=task_kind,
                policy=policy,
                context=context,
                selected=fallback,
                registry_name=policy.fallback_model,
                signals=signals,
                scored=[],
                reasons=["no eligible candidate; used policy fallback"],
            )

        scored = self._score_candidates(
            candidates,
            policy,
            context,
        )
        scored.sort(key=lambda item: item.composite_score)
        winner = scored[0]
        selected = self._registry.get(winner.model_name)

        reasons = [
            f"task={task_kind.value} via {task_source}",
            f"policy={policy.name}",
            (
                "weights adjusted for "
                f"prefer_low_cost={context.prefer_low_cost} "
                f"prefer_low_latency={context.prefer_low_latency}"
            ),
            f"selected {winner.model_name} composite={winner.composite_score:.4f}",
        ]

        cost_w, latency_w, pref_w = policy.normalized_weights(
            prefer_low_cost=context.prefer_low_cost,
            prefer_low_latency=context.prefer_low_latency,
        )

        return self._build_report(
            task_kind=task_kind,
            policy=policy,
            context=context,
            selected=selected,
            registry_name=winner.model_name,
            signals=signals,
            scored=scored,
            reasons=reasons,
            cost_weight=cost_w,
            latency_weight=latency_w,
            preference_weight=pref_w,
            winner=winner,
        )

    def _collect_candidates(
        self,
        policy: RoutePolicy,
        context: RoutingContext,
        task_kind: TaskKind,
    ) -> list[tuple[str, ModelInfo]]:
        min_ctx = max(
            policy.min_context_length,
            context.min_context_length or 0,
        )

        pool: dict[str, ModelInfo] = {}

        for name in policy.preferred_models:
            try:
                info = self._registry.get(name)
            except KeyError:
                continue
            if self._eligible(info, policy, min_ctx, context):
                pool[name] = info

        if policy.required_capabilities:
            for info in self._registry.list_models():
                if info.name in pool:
                    continue
                if self._eligible(info, policy, min_ctx, context):
                    pool[info.name] = info

        if not pool:
            for name in policy.preferred_models:
                try:
                    pool[name] = self._registry.get(name)
                except KeyError:
                    continue

        return list(pool.items())

    def _eligible(
        self,
        info: ModelInfo,
        policy: RoutePolicy,
        min_ctx: int,
        context: RoutingContext,
    ) -> bool:
        caps = {c.lower() for c in info.capabilities}
        if policy.required_capabilities:
            required = {c.lower() for c in policy.required_capabilities}
            if not required.intersection(caps):
                return False

        if min_ctx and info.context_length < min_ctx:
            return False

        if context.max_cost_per_1m is not None:
            blended = _blended_cost(info)
            if blended > context.max_cost_per_1m:
                return False

        return True

    def _score_candidates(
        self,
        candidates: list[tuple[str, ModelInfo]],
        policy: RoutePolicy,
        context: RoutingContext,
    ) -> list[ScoredCandidate]:
        costs = [_blended_cost(info) for _, info in candidates]
        latencies = [_estimated_latency_ms(info) for _, info in candidates]

        max_cost = max(costs) if costs else 1.0
        max_latency = max(latencies) if latencies else 1.0
        if max_cost <= 0:
            max_cost = 1.0
        if max_latency <= 0:
            max_latency = 1.0

        pref_rank = {
            name: index
            for index, name in enumerate(policy.preferred_models)
        }
        max_rank = max(len(policy.preferred_models), 1)

        cost_w, latency_w, pref_w = policy.normalized_weights(
            prefer_low_cost=context.prefer_low_cost,
            prefer_low_latency=context.prefer_low_latency,
        )

        scored: list[ScoredCandidate] = []
        for (name, info), cost, latency in zip(
            candidates,
            costs,
            latencies,
            strict=True,
        ):
            cost_norm = cost / max_cost
            latency_norm = latency / max_latency
            rank = pref_rank.get(name, max_rank)
            pref_norm = rank / max_rank

            composite = (
                cost_w * cost_norm
                + latency_w * latency_norm
                + pref_w * pref_norm
            )

            scored.append(
                ScoredCandidate(
                    model_name=name,
                    model_id=info.model_id,
                    cost_score=round(cost_norm, 4),
                    latency_score=round(latency_norm, 4),
                    preference_score=round(pref_norm, 4),
                    composite_score=round(composite, 4),
                    estimated_latency_ms=latency,
                    blended_cost_per_1m=round(cost, 4),
                )
            )

        return scored

    def _build_report(
        self,
        *,
        task_kind: TaskKind,
        policy: RoutePolicy,
        context: RoutingContext,
        selected: ModelInfo,
        registry_name: str,
        signals: dict[str, Any],
        scored: list[ScoredCandidate],
        reasons: list[str],
        cost_weight: float = 0.0,
        latency_weight: float = 0.0,
        preference_weight: float = 0.0,
        winner: ScoredCandidate | None = None,
    ) -> RoutingReport:
        return RoutingReport(
            task_type=task_kind,
            policy_name=policy.name,
            selected_model=selected,
            selected_registry_name=registry_name,
            reasons=reasons,
            prompt_signals=signals,
            cost_weight=cost_weight,
            latency_weight=latency_weight,
            preference_weight=preference_weight,
            winner=winner,
            candidates=scored,
        )


def get_router_engine() -> RouterEngine:
    global _default_engine

    with _engine_lock:
        if _default_engine is None:
            threshold = _long_context_threshold_from_settings()
            _default_engine = RouterEngine(
                long_context_threshold=threshold,
            )
        return _default_engine


def reset_router_engine() -> None:
    global _default_engine

    with _engine_lock:
        _default_engine = None


def _long_context_threshold_from_settings() -> int:
    try:
        from app.config.settings import get_settings

        return get_settings().MODEL_ROUTER_LONG_CONTEXT_CHARS
    except Exception:
        return 6000


def _blended_cost(info: ModelInfo) -> float:
    return (info.cost.input_per_1m + info.cost.output_per_1m) / 2.0


def _estimated_latency_ms(info: ModelInfo) -> float:
    raw = info.metadata.get("estimated_latency_ms")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass

    lower = info.model_id.lower()
    if "0.5b" in lower or "3b" in lower:
        return 400.0
    if "7b" in lower or "8b" in lower:
        return 800.0
    if "70b" in lower or "72b" in lower:
        return 2500.0
    if info.provider.value == "openai":
        return 600.0
    return 1000.0
