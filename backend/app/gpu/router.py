"""
GPU 管理 REST API。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

from app.gpu.manager import get_gpu_resource_manager
from app.gpu.types import GpuAllocationRequest
from app.gpu.types import GpuAllocationResult
from app.gpu.types import GpuStatusReport

router = APIRouter(prefix="/gpu", tags=["GPU Resource Manager"])


@router.get("/status", response_model=GpuStatusReport)
def gpu_status_report() -> GpuStatusReport:
    return get_gpu_resource_manager().build_status_report()


@router.get("/status/report.md", response_class=PlainTextResponse)
def gpu_status_report_markdown() -> str:
    report = get_gpu_resource_manager().build_status_report()
    return report.to_markdown()


@router.post("/allocate", response_model=GpuAllocationResult)
def gpu_allocate(body: GpuAllocationRequest) -> GpuAllocationResult:
    manager = get_gpu_resource_manager()
    result = manager.allocate_auto(body, use_scheduler=False)
    if not result.success:
        raise HTTPException(status_code=409, detail=result.message)
    return result


@router.post("/allocate/schedule", response_model=GpuAllocationResult)
def gpu_allocate_scheduled(body: GpuAllocationRequest) -> GpuAllocationResult:
    manager = get_gpu_resource_manager()
    result = manager.allocate_auto(body, use_scheduler=True)
    if not result.success:
        raise HTTPException(status_code=409, detail=result.message)
    return result


@router.post("/release/{allocation_id}")
def gpu_release(allocation_id: str) -> dict[str, bool]:
    released = get_gpu_resource_manager().release(allocation_id)
    if not released:
        raise HTTPException(status_code=404, detail="allocation not found")
    return {"released": True}
