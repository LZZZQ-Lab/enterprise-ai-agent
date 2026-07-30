"""
GPU Allocator：按显存与负载自动选卡。
"""

from __future__ import annotations

import threading
import uuid

from app.gpu.monitor import GPUMonitor
from app.gpu.types import GpuAllocationRecord
from app.gpu.types import GpuAllocationRequest
from app.gpu.types import GpuAllocationResult
from app.gpu.types import GpuDeviceState


class GPUAllocator:
    """
    跟踪逻辑显存配额，并结合 Monitor 快照做自动分配。
    """

    def __init__(self, monitor: GPUMonitor | None = None) -> None:
        self._monitor = monitor or GPUMonitor()
        self._lock = threading.RLock()
        self._allocations: dict[str, GpuAllocationRecord] = {}

    @property
    def monitor(self) -> GPUMonitor:
        return self._monitor

    def list_allocations(self) -> list[GpuAllocationRecord]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in self._allocations.values()
            ]

    def allocate(self, request: GpuAllocationRequest) -> GpuAllocationResult:
        with self._lock:
            devices = self._monitor.scan_devices()
            if not devices:
                return GpuAllocationResult(
                    success=False,
                    message="No GPU devices detected (nvidia-smi unavailable?)",
                )

            chosen: list[int] = []
            allocation_ids: list[str] = []

            for _ in range(request.gpu_count):
                gpu_index = self._pick_gpu_index(
                    devices,
                    request=request,
                    exclude=set(chosen),
                )
                if gpu_index is None:
                    self._rollback_allocations(allocation_ids)
                    return GpuAllocationResult(
                        success=False,
                        message=(
                            "Insufficient GPU memory for "
                            f"{request.memory_mib} MiB"
                        ),
                    )

                record = GpuAllocationRecord(
                    allocation_id=uuid.uuid4().hex,
                    gpu_index=gpu_index,
                    memory_mib=request.memory_mib,
                    owner=request.owner,
                    purpose=request.purpose,
                    metadata=dict(request.metadata),
                )
                self._allocations[record.allocation_id] = record
                allocation_ids.append(record.allocation_id)
                chosen.append(gpu_index)
                self._apply_allocation_to_device(devices, record)

            return GpuAllocationResult(
                success=True,
                allocation_ids=allocation_ids,
                gpu_indices=chosen,
                message="allocated",
            )

    def release(self, allocation_id: str) -> bool:
        with self._lock:
            return self._allocations.pop(allocation_id, None) is not None

    def release_all(self, owner: str | None = None) -> int:
        with self._lock:
            if not owner:
                count = len(self._allocations)
                self._allocations.clear()
                return count

            to_remove = [
                key
                for key, value in self._allocations.items()
                if value.owner == owner
            ]
            for key in to_remove:
                self._allocations.pop(key, None)
            return len(to_remove)

    def merge_device_allocations(
        self,
        devices: list[GpuDeviceState],
    ) -> list[GpuDeviceState]:
        """将逻辑分配叠加到设备视图。"""

        totals: dict[int, tuple[float, int]] = {}
        with self._lock:
            for record in self._allocations.values():
                used, count = totals.get(record.gpu_index, (0.0, 0))
                totals[record.gpu_index] = (
                    used + record.memory_mib,
                    count + 1,
                )

        merged: list[GpuDeviceState] = []
        for device in devices:
            allocated, count = totals.get(device.index, (0.0, 0))
            merged.append(
                device.model_copy(
                    update={
                        "allocated_mib": allocated,
                        "allocation_count": count,
                    },
                )
            )
        return merged

    def _pick_gpu_index(
        self,
        devices: list[GpuDeviceState],
        *,
        request: GpuAllocationRequest,
        exclude: set[int],
    ) -> int | None:
        candidates: list[tuple[float, float, int]] = []

        preferred = set(request.preferred_indices or [])
        for device in devices:
            if device.index in exclude:
                continue
            if preferred and device.index not in preferred:
                continue

            free_mib = self._effective_free_mib(device)
            if free_mib < request.memory_mib:
                continue

            util = device.utilization_percent or 0.0
            temp = device.temperature_c or 0.0
            # 分数越低越优先：负载 + 温度软惩罚
            score = util + temp * 0.05
            if preferred:
                score -= 10.0
            candidates.append((score, free_mib, device.index))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], -item[1]))
        return candidates[0][2]

    @staticmethod
    def _effective_free_mib(device: GpuDeviceState) -> float:
        if device.memory_free_mib is not None:
            free = device.memory_free_mib
        elif (
            device.memory_total_mib is not None
            and device.memory_used_mib is not None
        ):
            free = device.memory_total_mib - device.memory_used_mib
        else:
            free = 0.0
        free -= device.allocated_mib
        return max(0.0, free)

    @staticmethod
    def _apply_allocation_to_device(
        devices: list[GpuDeviceState],
        record: GpuAllocationRecord,
    ) -> None:
        for device in devices:
            if device.index == record.gpu_index:
                device.allocated_mib += record.memory_mib
                device.allocation_count += 1
                return

    def _rollback_allocations(self, allocation_ids: list[str]) -> None:
        for allocation_id in allocation_ids:
            self._allocations.pop(allocation_id, None)
