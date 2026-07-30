"""Task 7.4 GPU Resource Manager 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.gpu.allocator import GPUAllocator
from app.gpu.manager import GpuResourceManager
from app.gpu.monitor import GPUMonitor
from app.gpu.types import GpuAllocationRequest
from app.gpu.types import GpuDeviceState
from app.gpu.types import GpuDeviceStatus


def _sample_devices() -> list[GpuDeviceState]:
    return [
        GpuDeviceState(
            index=0,
            name="GPU-A",
            status=GpuDeviceStatus.AVAILABLE,
            memory_used_mib=1000,
            memory_total_mib=8000,
            memory_free_mib=7000,
            utilization_percent=10,
            temperature_c=55,
        ),
        GpuDeviceState(
            index=1,
            name="GPU-B",
            status=GpuDeviceStatus.BUSY,
            memory_used_mib=6000,
            memory_total_mib=8000,
            memory_free_mib=2000,
            utilization_percent=80,
            temperature_c=72,
        ),
    ]


def test_monitor_parse_and_scan() -> None:
    monitor = GPUMonitor()
    fake_output = "0, NVIDIA A100, 12, 1024, 8192, 63\n"

    with patch.object(
        monitor,
        "nvidia_smi_available",
        return_value=True,
    ), patch(
        "app.gpu.monitor.subprocess.check_output",
        return_value=fake_output,
    ):
        devices = monitor.scan_devices()

    assert len(devices) == 1
    assert devices[0].index == 0
    assert devices[0].memory_total_mib == 8192
    assert devices[0].temperature_c == 63


def test_allocator_picks_lower_load_gpu() -> None:
    monitor = GPUMonitor()
    allocator = GPUAllocator(monitor)

    with patch.object(monitor, "scan_devices", return_value=_sample_devices()):
        result = allocator.allocate(
            GpuAllocationRequest(memory_mib=4096, owner="test"),
        )

    assert result.success is True
    assert result.gpu_indices == [0]


def test_allocator_respects_insufficient_memory() -> None:
    monitor = GPUMonitor()
    allocator = GPUAllocator(monitor)

    with patch.object(monitor, "scan_devices", return_value=_sample_devices()):
        result = allocator.allocate(
            GpuAllocationRequest(memory_mib=7500),
        )

    assert result.success is False


def test_status_report_contains_summary() -> None:
    monitor = GPUMonitor()
    manager = GpuResourceManager(monitor=monitor, allocator=GPUAllocator(monitor))

    with patch.object(monitor, "scan_devices", return_value=_sample_devices()):
        report = manager.build_status_report()

    assert report.device_count == 2
    assert report.summary["available_devices"] == 1
    assert "avg_temperature_c" in report.summary
    markdown = report.to_markdown()
    assert "GPU Status Report" in markdown


def test_release_allocation() -> None:
    monitor = GPUMonitor()
    allocator = GPUAllocator(monitor)

    with patch.object(monitor, "scan_devices", return_value=_sample_devices()):
        created = allocator.allocate(
            GpuAllocationRequest(memory_mib=1024, owner="worker"),
        )

    assert created.success
    allocation_id = created.allocation_ids[0]
    assert allocator.release(allocation_id) is True
    assert allocator.release(allocation_id) is False
