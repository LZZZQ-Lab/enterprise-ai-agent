"""
Dispatcher — 连接 TaskQueue 与 Worker 池。
"""

from __future__ import annotations

import threading
from typing import Callable

from app.scheduler.queue import TaskQueue
from app.scheduler.worker import ExecuteFn
from app.scheduler.worker import Worker


class Dispatcher:
    """
    维护 worker 池，从 queue 拉取 task_id 并分发执行。
    """

    def __init__(
        self,
        queue: TaskQueue,
        *,
        execute_fn: ExecuteFn,
        worker_count: int = 4,
        pop_timeout: float = 0.5,
    ) -> None:

        self._queue = queue
        self._execute_fn = execute_fn
        self._pop_timeout = pop_timeout
        self._lock = threading.Lock()
        self._workers: list[Worker] = []
        self._started = False

        for index in range(max(1, worker_count)):
            worker = Worker(
                index,
                claim_task=self._claim,
                execute_fn=execute_fn,
                idle_timeout=pop_timeout,
            )
            self._workers.append(worker)

    def _claim(self) -> str | None:

        return self._queue.pop(timeout=self._pop_timeout)

    def start(self) -> None:

        with self._lock:
            if self._started:
                return

            for worker in self._workers:
                worker.start()

            self._started = True

    def stop(self) -> None:

        with self._lock:
            for worker in self._workers:
                worker.stop()

            self._started = False

    @property
    def worker_count(self) -> int:

        return len(self._workers)
