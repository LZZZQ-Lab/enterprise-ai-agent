"""
GPU Monitor：采集显存、利用率、温度。
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from datetime import datetime
from datetime import timezone

from app.gpu.types import GpuDeviceState
from app.gpu.types import GpuDeviceStatus


class GPUMonitor:
    """
    通过 nvidia-smi 监控全部 GPU；无 GPU 时返回空列表。
    """

    _QUERY_FIELDS = (
        "index,name,utilization.gpu,memory.used,memory.total,temperature.gpu"
    )

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_scan: datetime | None = None
        self._cached_devices: list[GpuDeviceState] = []

    @property
    def last_scan(self) -> datetime | None:
        return self._last_scan

    def nvidia_smi_available(self) -> bool:
        return shutil.which("nvidia-smi") is not None

    def scan_devices(self) -> list[GpuDeviceState]:
        with self._lock:
            devices = self._collect_from_nvidia_smi()
            self._cached_devices = devices
            self._last_scan = datetime.now(timezone.utc)
            return [item.model_copy(deep=True) for item in devices]

    def get_cached_devices(self) -> list[GpuDeviceState]:
        with self._lock:
            if not self._cached_devices:
                return self.scan_devices()
            return [
                item.model_copy(deep=True) for item in self._cached_devices
            ]

    def _collect_from_nvidia_smi(self) -> list[GpuDeviceState]:
        if not self.nvidia_smi_available():
            return []

        try:
            output = subprocess.check_output(
                [
                    "nvidia-smi",
                    f"--query-gpu={self._QUERY_FIELDS}",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=15,
            )
        except (
            subprocess.SubprocessError,
            OSError,
            ValueError,
        ):
            return []

        devices: list[GpuDeviceState] = []
        for line in output.strip().splitlines():
            parsed = self._parse_line(line)
            if parsed is not None:
                devices.append(parsed)

        return sorted(devices, key=lambda item: item.index)

    @staticmethod
    def _parse_line(line: str) -> GpuDeviceState | None:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            return None

        try:
            index = int(parts[0])
            name = parts[1]
            util = _to_float(parts[2])
            used = _to_float(parts[3])
            total = _to_float(parts[4])
            temp = _to_float(parts[5])
        except (ValueError, IndexError):
            return None

        free = None
        if used is not None and total is not None:
            free = max(0.0, total - used)

        status = GpuDeviceStatus.AVAILABLE
        if util is not None and util >= 95:
            status = GpuDeviceStatus.BUSY

        return GpuDeviceState(
            index=index,
            name=name,
            status=status,
            memory_used_mib=used,
            memory_total_mib=total,
            memory_free_mib=free,
            utilization_percent=util,
            temperature_c=temp,
        )


def _to_float(raw: str) -> float | None:
    text = raw.strip()
    if not text or text.upper() in {"N/A", "[N/A]"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None
