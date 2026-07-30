"""
AgentScheduler — 企业级 Agent 任务调度（FIFO / 优先级、重试、取消、超时）。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from uuid import uuid4

from app.agents.runtime import AgentTask
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.scheduler.dispatcher import Dispatcher
from app.scheduler.queue import QueuePolicy
from app.scheduler.queue import SchedulerTaskRecord
from app.scheduler.queue import TaskStatus
from app.scheduler.queue import create_task_queue
from app.scheduler.worker import TimeoutExecutor

AgentExecuteFn = Callable[
    [AgentTask, AgentConfig | None, dict[str, Any]],
    AgentResult,
]


@dataclass
class _TaskPayload:
    agent_task: AgentTask
    config: AgentConfig | None = None
    agent_kwargs: dict[str, Any] = field(default_factory=dict)
    done_event: threading.Event = field(default_factory=threading.Event)


class AgentScheduler:
    """
    统一 Agent 执行入口：Runtime.run 提交到此调度器，Worker 回调 execute_fn。
    """

    def __init__(
        self,
        *,
        policy: QueuePolicy = QueuePolicy.FIFO,
        worker_count: int = 4,
        max_exec_threads: int = 8,
        auto_start: bool = True,
    ) -> None:

        self._policy = policy
        self._queue = create_task_queue(policy)
        self._records: dict[str, SchedulerTaskRecord] = {}
        self._payloads: dict[str, _TaskPayload] = {}
        self._lock = threading.RLock()
        self._execute_fn: AgentExecuteFn | None = None
        self._timeout_executor = TimeoutExecutor(max_workers=max_exec_threads)
        self._dispatcher = Dispatcher(
            self._queue,
            execute_fn=self._on_worker_task,
            worker_count=worker_count,
        )

        if auto_start:
            self.start()

    def set_executor(self, fn: AgentExecuteFn) -> None:
        """绑定 Agent 执行函数（通常为 AgentRuntime.execute_task）。"""

        self._execute_fn = fn

    def start(self) -> None:

        self._dispatcher.start()

    def stop(self) -> None:

        self._dispatcher.stop()
        self._timeout_executor.shutdown(wait=True)

    @property
    def policy(self) -> QueuePolicy:

        return self._policy

    def submit(
        self,
        task: AgentTask,
        *,
        priority: int = 0,
        timeout_sec: float | None = None,
        max_retries: int = 0,
        config: AgentConfig | None = None,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> str:
        """
        异步入队，返回 task_id。
        """

        task_id = uuid4().hex[:16]
        now = time.time()

        record = SchedulerTaskRecord(
            task_id=task_id,
            status=TaskStatus.PENDING,
            priority=priority,
            max_retries=max_retries,
            timeout_sec=timeout_sec,
            enqueued_at=now,
        )

        payload = _TaskPayload(
            agent_task=task,
            config=config,
            agent_kwargs=dict(agent_kwargs or {}),
        )

        with self._lock:
            self._records[task_id] = record
            self._payloads[task_id] = payload
            self._queue.push(task_id, priority=priority, enqueued_at=now)

        return task_id

    def submit_and_wait(
        self,
        task: AgentTask,
        *,
        priority: int = 0,
        timeout_sec: float | None = None,
        max_retries: int = 0,
        config: AgentConfig | None = None,
        agent_kwargs: dict[str, Any] | None = None,
        wait_timeout: float | None = None,
    ) -> AgentResult:

        task_id = self.submit(
            task,
            priority=priority,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            config=config,
            agent_kwargs=agent_kwargs,
        )

        payload = self._payloads[task_id]
        deadline = None

        if wait_timeout is not None:
            deadline = time.time() + wait_timeout

        while True:
            remaining = None

            if deadline is not None:
                remaining = max(0.0, deadline - time.time())

                if remaining == 0.0 and not payload.done_event.is_set():
                    self.cancel(task_id)
                    return AgentResult(
                        success=False,
                        model="scheduler",
                        content="submit_and_wait timed out",
                    )

            if payload.done_event.wait(timeout=remaining if deadline else 0.5):
                break

        record = self.get_record(task_id)

        if record is None:
            return AgentResult(
                success=False,
                model="scheduler",
                content="task record missing",
            )

        if record.status == TaskStatus.SUCCESS and isinstance(
            record.result,
            AgentResult,
        ):
            return record.result

        error = record.error or f"task ended with status {record.status.value}"

        return AgentResult(
            success=False,
            model="scheduler",
            content=error,
        )

    def cancel(self, task_id: str) -> bool:
        """
        取消 PENDING 任务；RUNNING 任务标记 cancelled，执行层尽力中断。
        """

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                return False

            if record.status in (
                TaskStatus.SUCCESS,
                TaskStatus.FAILED,
                TaskStatus.TIMEOUT,
                TaskStatus.CANCELLED,
            ):
                return False

            record.cancelled = True

            if record.status == TaskStatus.PENDING:
                record.status = TaskStatus.CANCELLED
                record.finished_at = time.time()
                self._queue.remove(task_id)
                payload = self._payloads.get(task_id)

                if payload is not None:
                    payload.done_event.set()

                return True

            return True

    def get_record(self, task_id: str) -> SchedulerTaskRecord | None:

        with self._lock:
            rec = self._records.get(task_id)

            if rec is None:
                return None

            return SchedulerTaskRecord(
                task_id=rec.task_id,
                status=rec.status,
                priority=rec.priority,
                max_retries=rec.max_retries,
                retry_count=rec.retry_count,
                timeout_sec=rec.timeout_sec,
                error=rec.error,
                result=rec.result,
                cancelled=rec.cancelled,
                enqueued_at=rec.enqueued_at,
                started_at=rec.started_at,
                finished_at=rec.finished_at,
            )

    def _on_worker_task(self, task_id: str) -> None:

        with self._lock:
            record = self._records.get(task_id)
            payload = self._payloads.get(task_id)

            if record is None or payload is None:
                return

            if record.cancelled or record.status != TaskStatus.PENDING:
                return

            record.status = TaskStatus.RUNNING
            record.started_at = time.time()

        if self._execute_fn is None:
            self._finalize(
                task_id,
                status=TaskStatus.FAILED,
                error="scheduler executor not configured",
                result=None,
            )
            return

        if record.cancelled:
            self._finalize(
                task_id,
                status=TaskStatus.CANCELLED,
                error="cancelled before run",
                result=None,
            )
            return

        def _run_once() -> AgentResult:
            return self._execute_fn(
                payload.agent_task,
                payload.config,
                payload.agent_kwargs,
            )

        result_value, terminal, err = self._timeout_executor.run(
            _run_once,
            timeout_sec=record.timeout_sec,
        )

        with self._lock:
            record = self._records[task_id]

            if record is None:
                return

            if record.cancelled and terminal != TaskStatus.TIMEOUT:
                self._finalize(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    error="cancelled during run",
                    result=result_value,
                )
                return

        if terminal == TaskStatus.SUCCESS:
            agent_result = result_value

            if isinstance(agent_result, AgentResult) and agent_result.success:
                self._finalize(
                    task_id,
                    status=TaskStatus.SUCCESS,
                    error="",
                    result=agent_result,
                )
                return

            err_msg = ""

            if isinstance(agent_result, AgentResult):
                err_msg = agent_result.content or "agent returned success=False"
            else:
                err_msg = err or "invalid agent result"

            self._handle_failure(task_id, error=err_msg)
            return

        if terminal == TaskStatus.TIMEOUT:
            self._handle_failure(
                task_id,
                error=err or "timeout",
                force_status=TaskStatus.TIMEOUT,
            )
            return

        self._handle_failure(task_id, error=err or "execution failed")

    def _handle_failure(
        self,
        task_id: str,
        *,
        error: str,
        force_status: TaskStatus | None = None,
    ) -> None:

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                return

            if force_status == TaskStatus.TIMEOUT:
                if (
                    record.retry_count < record.max_retries
                    and not record.cancelled
                ):
                    record.retry_count += 1
                    record.status = TaskStatus.PENDING
                    record.error = error
                    self._queue.push(
                        task_id,
                        priority=record.priority,
                        enqueued_at=time.time(),
                    )
                    return

                self._finalize(
                    task_id,
                    status=TaskStatus.TIMEOUT,
                    error=error,
                    result=None,
                )
                return

            if record.retry_count < record.max_retries and not record.cancelled:
                record.retry_count += 1
                record.status = TaskStatus.PENDING
                record.error = error
                self._queue.push(
                    task_id,
                    priority=record.priority,
                    enqueued_at=time.time(),
                )
                return

            self._finalize(
                task_id,
                status=TaskStatus.FAILED,
                error=error,
                result=None,
            )

    def _finalize(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        error: str,
        result: Any,
    ) -> None:

        with self._lock:
            record = self._records.get(task_id)
            payload = self._payloads.get(task_id)

            if record is None:
                return

            record.status = status
            record.error = error
            record.result = result
            record.finished_at = time.time()

            if payload is not None:
                payload.done_event.set()

    def dashboard_snapshot(self) -> dict[str, object]:
        """Task 7.8：Agent 调度队列摘要。"""

        with self._lock:
            records = list(self._records.values())

        counts: dict[str, int] = {}
        for record in records:
            status = (
                record.status.value
                if hasattr(record.status, "value")
                else str(record.status)
            )
            counts[status] = counts.get(status, 0) + 1

        return {
            "worker_count": self._dispatcher.worker_count,
            "queue_policy": self._policy.value,
            "tasks_total": len(records),
            "tasks_by_status": counts,
            "auto_started": bool(
                getattr(self._dispatcher, "_started", False),
            ),
        }


_default_scheduler: AgentScheduler | None = None
_default_scheduler_lock = threading.Lock()


def get_default_scheduler(
    *,
    policy: QueuePolicy = QueuePolicy.FIFO,
    worker_count: int = 4,
) -> AgentScheduler:

    global _default_scheduler

    with _default_scheduler_lock:
        if _default_scheduler is None:
            _default_scheduler = AgentScheduler(
                policy=policy,
                worker_count=worker_count,
                auto_start=True,
            )

        return _default_scheduler
