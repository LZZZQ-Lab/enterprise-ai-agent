"""
Task 4.5：GPU 与服务指标采集，供 ``/metrics`` 刮取。
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from app.monitoring.metrics import METRIC_GPU_MEMORY_TOTAL
from app.monitoring.metrics import METRIC_GPU_MEMORY_USED
from app.monitoring.metrics import METRIC_GPU_UTILIZATION
from app.monitoring.metrics import METRIC_GPU_TEMPERATURE
from app.monitoring.metrics import InfraMetricsRegistry
from app.monitoring.metrics import infra_metrics


@dataclass
class GpuSnapshot:
    """单 GPU 快照（多卡时取 index 0）。"""

    memory_used_mib: float | None
    memory_total_mib: float | None
    utilization_percent: float | None
    gpu_index: int = 0


def collect_gpu_snapshot(
    gpu_index: int = 0,
) -> GpuSnapshot:
    """
    通过 nvidia-smi 采集显存与 GPU 利用率。
    """

    if shutil.which("nvidia-smi") is None:

        return GpuSnapshot(None, None, None, gpu_index)

    try:

        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
                f"--id={gpu_index}",
            ],
            text=True,
            timeout=10,
        )

        line = out.strip().splitlines()[0]
        util, used, total = (
            float(part.strip())
            for part in line.split(",")
        )

        return GpuSnapshot(
            memory_used_mib=used,
            memory_total_mib=total,
            utilization_percent=util,
            gpu_index=gpu_index,
        )

    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        IndexError,
    ):

        return GpuSnapshot(None, None, None, gpu_index)


class InfraMetricsCollector:
    """
    刮取前刷新 GPU Gauge，并合并进程内服务指标。
    """

    def __init__(
        self,
        registry: InfraMetricsRegistry | None = None,
        *,
        gpu_index: int = 0,
    ) -> None:

        self._registry = registry or infra_metrics
        self._gpu_index = gpu_index

    def refresh_gpu_gauges(self) -> GpuSnapshot:
        """
        刷新 Prometheus GPU Gauge（多卡）；返回 index 0 快照以兼容旧接口。
        """

        from app.gpu.monitor import GPUMonitor

        monitor = GPUMonitor()
        devices = monitor.scan_devices()

        if not devices:
            snap = collect_gpu_snapshot(self._gpu_index)
            labels = {"gpu": str(snap.gpu_index)}
            self._push_snapshot_gauges(snap, labels)
            return snap

        for device in devices:
            labels = {"gpu": str(device.index)}
            if device.memory_used_mib is not None:
                self._registry.gauge_set(
                    METRIC_GPU_MEMORY_USED,
                    device.memory_used_mib,
                    labels=labels,
                )
            if device.memory_total_mib is not None:
                self._registry.gauge_set(
                    METRIC_GPU_MEMORY_TOTAL,
                    device.memory_total_mib,
                    labels=labels,
                )
            if device.utilization_percent is not None:
                self._registry.gauge_set(
                    METRIC_GPU_UTILIZATION,
                    device.utilization_percent,
                    labels=labels,
                )
            if device.temperature_c is not None:
                self._registry.gauge_set(
                    METRIC_GPU_TEMPERATURE,
                    device.temperature_c,
                    labels=labels,
                )

        first = devices[0]
        return GpuSnapshot(
            memory_used_mib=first.memory_used_mib,
            memory_total_mib=first.memory_total_mib,
            utilization_percent=first.utilization_percent,
            gpu_index=first.index,
        )

    def _push_snapshot_gauges(
        self,
        snap: GpuSnapshot,
        labels: dict[str, str],
    ) -> None:
        # 无 GPU / nvidia-smi 时仍写出 0，保证 /metrics 始终有 # TYPE 行（CI 友好）
        self._registry.gauge_set(
            METRIC_GPU_MEMORY_USED,
            snap.memory_used_mib if snap.memory_used_mib is not None else 0.0,
            labels=labels,
        )
        self._registry.gauge_set(
            METRIC_GPU_MEMORY_TOTAL,
            snap.memory_total_mib if snap.memory_total_mib is not None else 0.0,
            labels=labels,
        )
        self._registry.gauge_set(
            METRIC_GPU_UTILIZATION,
            (
                snap.utilization_percent
                if snap.utilization_percent is not None
                else 0.0
            ),
            labels=labels,
        )

    def scrape(self) -> str:
        """Prometheus 文本（含最新 GPU + 服务 Counter/Histogram）。"""

        self.refresh_gpu_gauges()

        return self._registry.render_prometheus()


default_collector = InfraMetricsCollector()
