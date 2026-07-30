"""
GPU 资源管理器：Monitor + Allocator + Scheduler + 状态报告。
"""

from __future__ import annotations

import threading

from app.gpu.allocator import GPUAllocator
from app.gpu.monitor import GPUMonitor
from app.gpu.scheduler import GPUScheduler
from app.gpu.types import GpuAllocationRequest
from app.gpu.types import GpuAllocationResult
from app.gpu.types import GpuDeviceStatus
from app.gpu.types import GpuStatusReport

_manager_lock = threading.Lock()
_default_manager: GpuResourceManager | None = None


class GpuResourceManager:
    """
    企业 GPU 统一管理入口。
    """

    def __init__(
        self,
        monitor: GPUMonitor | None = None,
        allocator: GPUAllocator | None = None,
        scheduler: GPUScheduler | None = None,
    ) -> None:
        self.monitor = monitor or GPUMonitor()
        self.allocator = allocator or GPUAllocator(self.monitor)
        self.scheduler = scheduler or GPUScheduler(self.allocator)

    def build_status_report(self) -> GpuStatusReport:
        devices = self.monitor.scan_devices()
        devices = self.allocator.merge_device_allocations(devices)
        allocations = self.allocator.list_allocations()

        available = sum(
            1
            for dev in devices
            if dev.status == GpuDeviceStatus.AVAILABLE
        )
        avg_util = _average(
            [dev.utilization_percent for dev in devices],
        )
        avg_temp = _average([dev.temperature_c for dev in devices])

        summary = {
            "available_devices": available,
            "busy_devices": sum(
                1 for dev in devices if dev.status == GpuDeviceStatus.BUSY
            ),
            "active_allocations": len(allocations),
            "avg_utilization_percent": avg_util,
            "avg_temperature_c": avg_temp,
            "scheduler_pending_jobs": self.scheduler.pending_jobs,
        }

        return GpuStatusReport(
            nvidia_smi_available=self.monitor.nvidia_smi_available(),
            device_count=len(devices),
            devices=devices,
            active_allocations=allocations,
            summary=summary,
        )

    def allocate_auto(
        self,
        request: GpuAllocationRequest,
        *,
        use_scheduler: bool = False,
    ) -> GpuAllocationResult:
        if use_scheduler:
            return self.scheduler.submit_and_wait(request)
        return self.allocator.allocate(request)

    def release(self, allocation_id: str) -> bool:
        return self.allocator.release(allocation_id)


def get_gpu_resource_manager() -> GpuResourceManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = GpuResourceManager()
        return _default_manager


def reset_gpu_resource_manager() -> None:
    global _default_manager

    with _manager_lock:
        _default_manager = None


def _average(values: list[float | None]) -> float | None:
    nums = [value for value in values if value is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)
