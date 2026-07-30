"""
GPU 资源管理数据模型（Task 7.4）。
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class GpuDeviceStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class GpuDeviceState(BaseModel):
    """单卡实时状态。"""

    index: int
    name: str = ""
    status: GpuDeviceStatus = GpuDeviceStatus.UNKNOWN
    memory_used_mib: float | None = None
    memory_total_mib: float | None = None
    memory_free_mib: float | None = None
    utilization_percent: float | None = None
    temperature_c: float | None = None
    allocated_mib: float = 0.0
    allocation_count: int = 0


class GpuAllocationRecord(BaseModel):
    allocation_id: str
    gpu_index: int
    memory_mib: float
    owner: str = ""
    purpose: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class GpuAllocationRequest(BaseModel):
    memory_mib: float = Field(default=4096, ge=1)
    gpu_count: int = Field(default=1, ge=1)
    owner: str = ""
    purpose: str = "inference"
    preferred_indices: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GpuAllocationResult(BaseModel):
    success: bool
    allocation_ids: list[str] = Field(default_factory=list)
    gpu_indices: list[int] = Field(default_factory=list)
    message: str = ""


class GpuStatusReport(BaseModel):
    """GPU 状态报告。"""

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    nvidia_smi_available: bool = False
    device_count: int = 0
    devices: list[GpuDeviceState] = Field(default_factory=list)
    active_allocations: list[GpuAllocationRecord] = Field(
        default_factory=list,
    )
    summary: dict[str, Any] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "# GPU Status Report",
            "",
            f"- Generated: `{self.generated_at.isoformat()}`",
            f"- NVIDIA SMI: `{self.nvidia_smi_available}`",
            f"- Devices: `{self.device_count}`",
            "",
            "## Devices",
        ]
        for dev in self.devices:
            lines.append(
                f"- GPU {dev.index} `{dev.name}` status={dev.status.value} "
                f"mem={dev.memory_used_mib}/{dev.memory_total_mib} MiB "
                f"util={dev.utilization_percent}% temp={dev.temperature_c}°C "
                f"alloc={dev.allocated_mib} MiB ({dev.allocation_count})"
            )
        if self.active_allocations:
            lines.extend(["", "## Allocations"])
            for item in self.active_allocations:
                lines.append(
                    f"- `{item.allocation_id}` gpu={item.gpu_index} "
                    f"{item.memory_mib} MiB owner={item.owner} "
                    f"purpose={item.purpose}"
                )
        return "\n".join(lines)
