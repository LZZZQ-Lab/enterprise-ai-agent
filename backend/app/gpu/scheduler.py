"""
GPU Scheduler：分配请求排队与执行。
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from dataclasses import field

from app.gpu.allocator import GPUAllocator
from app.gpu.types import GpuAllocationRequest
from app.gpu.types import GpuAllocationResult


@dataclass
class _ScheduledJob:
    job_id: str
    request: GpuAllocationRequest
    enqueued_at: float
    result: GpuAllocationResult | None = None
    done: threading.Event = field(default_factory=threading.Event)


class GPUScheduler:
    """
    FIFO 调度器：资源不足时可等待重试（进程内）。
    """

    def __init__(
        self,
        allocator: GPUAllocator | None = None,
        *,
        max_wait_seconds: float = 30.0,
        retry_interval_seconds: float = 0.5,
    ) -> None:
        self._allocator = allocator or GPUAllocator()
        self._max_wait = max_wait_seconds
        self._retry_interval = retry_interval_seconds
        self._lock = threading.RLock()
        self._queue: deque[_ScheduledJob] = deque()
        self._history_count = 0

    @property
    def allocator(self) -> GPUAllocator:
        return self._allocator

    @property
    def pending_jobs(self) -> int:
        with self._lock:
            return len(self._queue)

    def submit_and_wait(
        self,
        request: GpuAllocationRequest,
    ) -> GpuAllocationResult:
        job = _ScheduledJob(
            job_id=uuid.uuid4().hex,
            request=request,
            enqueued_at=time.monotonic(),
        )

        with self._lock:
            self._queue.append(job)
            self._history_count += 1

        deadline = time.monotonic() + self._max_wait
        result: GpuAllocationResult | None = None

        while time.monotonic() < deadline:
            result = self._allocator.allocate(request)
            if result.success:
                break
            time.sleep(self._retry_interval)

        if result is None:
            result = GpuAllocationResult(
                success=False,
                message="scheduler timeout",
            )

        job.result = result
        job.done.set()

        with self._lock:
            if self._queue and self._queue[0].job_id == job.job_id:
                self._queue.popleft()
            else:
                self._queue = deque(
                    item
                    for item in self._queue
                    if item.job_id != job.job_id
                )

        return result

    def schedule_async(
        self,
        request: GpuAllocationRequest,
    ) -> str:
        """
        后台线程执行调度，返回 job_id。
        """

        job = _ScheduledJob(
            job_id=uuid.uuid4().hex,
            request=request,
            enqueued_at=time.monotonic(),
        )

        with self._lock:
            self._queue.append(job)
            self._history_count += 1

        thread = threading.Thread(
            target=self._run_job,
            args=(job,),
            daemon=True,
            name=f"gpu-scheduler-{job.job_id[:8]}",
        )
        thread.start()
        return job.job_id

    def get_job_result(
        self,
        job_id: str,
        *,
        timeout: float = 0.0,
    ) -> GpuAllocationResult | None:
        with self._lock:
            job = next(
                (item for item in self._queue if item.job_id == job_id),
                None,
            )
        if job is None:
            return None
        if timeout > 0:
            job.done.wait(timeout=timeout)
        elif not job.done.is_set():
            return None
        return job.result

    def _run_job(self, job: _ScheduledJob) -> None:
        deadline = time.monotonic() + self._max_wait
        result: GpuAllocationResult | None = None

        while time.monotonic() < deadline:
            result = self._allocator.allocate(job.request)
            if result.success:
                break
            time.sleep(self._retry_interval)

        if result is None:
            result = GpuAllocationResult(
                success=False,
                message="scheduler timeout",
            )

        job.result = result
        job.done.set()

        with self._lock:
            self._queue = deque(
                item
                for item in self._queue
                if item.job_id != job.job_id
            )
