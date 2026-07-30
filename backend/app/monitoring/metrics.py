"""
Task 4.5：AI Infra 指标注册与 Prometheus 文本导出。

与 ``app.observability``（Agent Trace）分离，面向 GPU / QPS / 延迟 / Token。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from dataclasses import field

LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
)


def _label_str(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    parts = [
        f'{key}="{_escape(value)}"'
        for key, value in sorted(labels.items())
    ]
    return "{" + ",".join(parts) + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclass
class _CounterState:
    values: dict[tuple[tuple[str, str], ...], float] = field(
        default_factory=dict,
    )


@dataclass
class _HistogramState:
    sums: dict[tuple[tuple[str, str], ...], float] = field(
        default_factory=dict,
    )
    counts: dict[tuple[tuple[str, str], ...], int] = field(
        default_factory=dict,
    )
    buckets: dict[tuple[tuple[str, str], ...], dict[float, int]] = (
        field(default_factory=dict)
    )


@dataclass
class _GaugeState:
    values: dict[tuple[tuple[str, str], ...], float] = field(
        default_factory=dict,
    )


class InfraMetricsRegistry:
    """
    线程安全的 Counter / Histogram / Gauge，输出 Prometheus exposition。
    """

    def __init__(self) -> None:

        self._lock = threading.Lock()
        self._counters: dict[str, _CounterState] = {}
        self._histograms: dict[str, _HistogramState] = {}
        self._gauges: dict[str, _GaugeState] = {}

    def counter_inc(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:

        key = self._label_key(labels)

        with self._lock:

            state = self._counters.setdefault(name, _CounterState())
            state.values[key] = state.values.get(key, 0.0) + value

    def histogram_observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        buckets: tuple[float, ...] = LATENCY_BUCKETS,
    ) -> None:

        key = self._label_key(labels)

        with self._lock:

            state = self._histograms.setdefault(name, _HistogramState())
            state.sums[key] = state.sums.get(key, 0.0) + value
            state.counts[key] = state.counts.get(key, 0) + 1

            bucket_map = state.buckets.setdefault(key, {})

            for bound in buckets:

                if value <= bound:

                    bucket_map[bound] = bucket_map.get(bound, 0) + 1

    def gauge_set(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:

        key = self._label_key(labels)

        with self._lock:

            state = self._gauges.setdefault(name, _GaugeState())
            state.values[key] = value

    @staticmethod
    def _label_key(
        labels: dict[str, str] | None,
    ) -> tuple[tuple[str, str], ...]:

        if not labels:

            return ()

        return tuple(sorted(labels.items()))

    def record_http_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_sec: float,
    ) -> None:

        labels = {
            "method": method.upper(),
            "route": route,
            "status": str(status_code),
        }

        self.counter_inc(
            "ai_infra_http_requests_total",
            labels=labels,
        )

        self.histogram_observe(
            "ai_infra_http_request_duration_seconds",
            duration_sec,
            labels={
                "method": method.upper(),
                "route": route,
            },
        )

    def record_llm_usage(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_sec: float,
    ) -> None:

        model_label = {"model": model or "unknown"}

        self.counter_inc(
            "ai_infra_llm_requests_total",
            labels=model_label,
        )

        self.histogram_observe(
            "ai_infra_llm_request_duration_seconds",
            duration_sec,
            labels=model_label,
        )

        if prompt_tokens > 0:

            self.counter_inc(
                "ai_infra_llm_tokens_total",
                value=float(prompt_tokens),
                labels={**model_label, "type": "prompt"},
            )

        if completion_tokens > 0:

            self.counter_inc(
                "ai_infra_llm_tokens_total",
                value=float(completion_tokens),
                labels={**model_label, "type": "completion"},
            )

    def render_prometheus(self) -> str:
        """生成 ``text/plain; version=0.0.4`` 文本。"""

        lines: list[str] = []

        with self._lock:

            for name, state in sorted(self._counters.items()):

                lines.append(f"# TYPE {name} counter")

                for label_key, value in sorted(state.values.items()):

                    labels = dict(label_key)
                    lines.append(
                        f"{name}{_label_str(labels)} {value}"
                    )

            for name, state in sorted(self._histograms.items()):

                lines.append(f"# TYPE {name} histogram")

                for label_key in sorted(state.counts.keys()):

                    labels = dict(label_key)
                    base = _label_str(labels)
                    bucket_map = state.buckets.get(label_key, {})
                    cumulative = 0

                    for bound in LATENCY_BUCKETS:

                        cumulative += bucket_map.get(bound, 0)
                        bucket_labels = {
                            **labels,
                            "le": str(bound),
                        }
                        lines.append(
                            f"{name}_bucket{_label_str(bucket_labels)} "
                            f"{cumulative}"
                        )

                    plus_labels = {**labels, "le": "+Inf"}
                    count = state.counts[label_key]
                    lines.append(
                        f"{name}_bucket{_label_str(plus_labels)} {count}"
                    )
                    lines.append(
                        f"{name}_sum{base} {state.sums[label_key]}"
                    )
                    lines.append(
                        f"{name}_count{base} {count}"
                    )

            for name, state in sorted(self._gauges.items()):

                lines.append(f"# TYPE {name} gauge")

                for label_key, value in sorted(state.values.items()):

                    labels = dict(label_key)
                    lines.append(
                        f"{name}{_label_str(labels)} {value}"
                    )

        return "\n".join(lines) + "\n"

    def summarize(self) -> dict[str, object]:
        """
        供 AI Infra Dashboard 使用的进程内指标摘要（Task 7.8）。
        """

        with self._lock:
            http_total = 0.0
            http_errors = 0.0
            http_state = self._counters.get("ai_infra_http_requests_total")
            if http_state is not None:
                for label_key, value in http_state.values.items():
                    http_total += value
                    labels = dict(label_key)
                    status = labels.get("status", "200")
                    try:
                        if int(status) >= 400:
                            http_errors += value
                    except ValueError:
                        pass

            latency_state = self._histograms.get(
                "ai_infra_http_request_duration_seconds",
            )
            http_latency_avg_ms = 0.0
            http_latency_count = 0
            if latency_state is not None:
                total_sum = sum(latency_state.sums.values())
                total_count = sum(latency_state.counts.values())
                if total_count > 0:
                    http_latency_avg_ms = (
                        total_sum / total_count
                    ) * 1000.0
                    http_latency_count = total_count

            llm_models: dict[str, dict[str, float]] = {}
            llm_req = self._counters.get("ai_infra_llm_requests_total")
            if llm_req is not None:
                for label_key, count in llm_req.values.items():
                    model = dict(label_key).get("model", "unknown")
                    llm_models.setdefault(model, {"requests": 0.0})
                    llm_models[model]["requests"] += count

            llm_tokens = self._counters.get("ai_infra_llm_tokens_total")
            if llm_tokens is not None:
                for label_key, tokens in llm_tokens.values.items():
                    labels = dict(label_key)
                    model = labels.get("model", "unknown")
                    token_type = labels.get("type", "prompt")
                    bucket = llm_models.setdefault(
                        model,
                        {"requests": 0.0},
                    )
                    bucket[f"tokens_{token_type}"] = (
                        bucket.get(f"tokens_{token_type}", 0.0) + tokens
                    )

            llm_latency = self._histograms.get(
                "ai_infra_llm_request_duration_seconds",
            )
            if llm_latency is not None:
                for label_key, count in llm_latency.counts.items():
                    model = dict(label_key).get("model", "unknown")
                    if count <= 0:
                        continue
                    avg_sec = (
                        llm_latency.sums[label_key] / count
                    )
                    llm_models.setdefault(model, {"requests": 0.0})
                    llm_models[model]["latency_avg_ms"] = round(
                        avg_sec * 1000.0,
                        2,
                    )

            gpu_devices: list[dict[str, object]] = []
            for metric, field in (
                (METRIC_GPU_UTILIZATION, "utilization_percent"),
                (METRIC_GPU_MEMORY_USED, "memory_used_mib"),
                (METRIC_GPU_MEMORY_TOTAL, "memory_total_mib"),
                (METRIC_GPU_TEMPERATURE, "temperature_c"),
            ):
                gauge = self._gauges.get(metric)
                if gauge is None:
                    continue
                for label_key, value in gauge.values.items():
                    gpu_index = dict(label_key).get("gpu", "0")
                    while len(gpu_devices) <= int(gpu_index):
                        gpu_devices.append(
                            {"index": len(gpu_devices)},
                        )
                    gpu_devices[int(gpu_index)][field] = value

        error_rate = 0.0
        if http_total > 0:
            error_rate = round(http_errors / http_total, 4)

        qps_estimate = 0.0
        if http_latency_count > 0 and http_latency_avg_ms > 0:
            qps_estimate = round(
                1000.0 / http_latency_avg_ms,
                2,
            )

        return {
            "http_requests_total": int(http_total),
            "http_errors_total": int(http_errors),
            "http_error_rate": error_rate,
            "http_latency_avg_ms": round(http_latency_avg_ms, 2),
            "http_qps_estimate": qps_estimate,
            "llm_by_model": llm_models,
            "gpu_devices": gpu_devices,
        }


infra_metrics = InfraMetricsRegistry()

# 指标名常量（文档 / 测试引用）
METRIC_GPU_MEMORY_USED = "ai_infra_gpu_memory_used_mib"
METRIC_GPU_MEMORY_TOTAL = "ai_infra_gpu_memory_total_mib"
METRIC_GPU_UTILIZATION = "ai_infra_gpu_utilization_percent"
METRIC_GPU_TEMPERATURE = "ai_infra_gpu_temperature_c"
