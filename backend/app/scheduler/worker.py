"""
Worker — 从 Dispatcher 领取任务并执行（带超时）。
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any
from typing import Callable

from app.scheduler.queue import TaskStatus

log = logging.getLogger(__name__)

ExecuteFn = Callable[[str], None]


class Worker:
    """
    单 worker 线程：阻塞等待 task_id，交给 execute_fn 处理。
    """

    def __init__(
        self,
        worker_id: int,
        *,
        claim_task: Callable[[], str | None],
        execute_fn: ExecuteFn,
        idle_timeout: float = 0.5,
    ) -> None:

        self._worker_id = worker_id
        self._claim_task = claim_task
        self._execute_fn = execute_fn
        self._idle_timeout = idle_timeout
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"agent-scheduler-worker-{self._worker_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, join_timeout: float = 5.0) -> None:

        self._stop.set()

        if self._thread is not None:
            self._thread.join(timeout=join_timeout)

    def _loop(self) -> None:

        while not self._stop.is_set():
            task_id = self._claim_task()

            if task_id is None:
                continue

            try:
                self._execute_fn(task_id)
            except Exception:
                log.exception(
                    "Worker %s failed executing task %s",
                    self._worker_id,
                    task_id,
                )


class TimeoutExecutor:
    """
    在独立线程池中执行 callable，支持超时取消 Future。
    """

    def __init__(self, max_workers: int = 4) -> None:

        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="agent-task-exec",
        )

    def shutdown(self, *, wait: bool = True) -> None:

        self._pool.shutdown(wait=wait, cancel_futures=True)

    def run(
        self,
        fn: Callable[[], Any],
        *,
        timeout_sec: float | None,
    ) -> tuple[Any | None, TaskStatus, str]:
        """
        返回 (result, terminal_status, error_message)。
        """

        future: Future[Any] = self._pool.submit(fn)

        if timeout_sec is None or timeout_sec <= 0:
            try:
                return future.result(), TaskStatus.SUCCESS, ""
            except Exception as exc:
                return None, TaskStatus.FAILED, str(exc)

        try:
            value = future.result(timeout=timeout_sec)
            return value, TaskStatus.SUCCESS, ""
        except FuturesTimeoutError:
            future.cancel()
            return None, TaskStatus.TIMEOUT, f"Task exceeded timeout {timeout_sec}s"
        except Exception as exc:
            return None, TaskStatus.FAILED, str(exc)
