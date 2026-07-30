"""
任务队列：FIFO 与优先级队列。
"""

from __future__ import annotations

import heapq
import threading
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class QueuePolicy(str, Enum):
    FIFO = "fifo"
    PRIORITY = "priority"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(order=True)
class _PriorityItem:
    sort_key: tuple[int, float, str] = field(compare=True)
    task_id: str = field(compare=False)


@dataclass
class SchedulerTaskRecord:
    """调度层任务元数据（与 AgentTask 分离存储）。"""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    max_retries: int = 0
    retry_count: int = 0
    timeout_sec: float | None = None
    error: str = ""
    result: Any = None
    cancelled: bool = False
    enqueued_at: float = 0.0
    started_at: float | None = None
    finished_at: float | None = None


class TaskQueue:
    """
    线程安全任务队列抽象。
    """

    def push(self, task_id: str, *, priority: int = 0, enqueued_at: float = 0.0) -> None:
        raise NotImplementedError

    def pop(self, timeout: float | None = None) -> str | None:
        raise NotImplementedError

    def remove(self, task_id: str) -> bool:
        raise NotImplementedError

    def qsize(self) -> int:
        raise NotImplementedError


class FIFOQueue(TaskQueue):
    def __init__(self) -> None:
        self._deque: deque[str] = deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def push(
        self,
        task_id: str,
        *,
        priority: int = 0,
        enqueued_at: float = 0.0,
    ) -> None:

        del priority, enqueued_at

        with self._not_empty:
            self._deque.append(task_id)
            self._not_empty.notify()

    def pop(self, timeout: float | None = None) -> str | None:

        with self._not_empty:
            if not self._deque:
                if timeout is None:
                    self._not_empty.wait()
                elif not self._not_empty.wait(timeout=timeout):
                    return None

            if not self._deque:
                return None

            return self._deque.popleft()

    def remove(self, task_id: str) -> bool:

        with self._lock:
            try:
                self._deque.remove(task_id)
                return True
            except ValueError:
                return False

    def qsize(self) -> int:

        with self._lock:
            return len(self._deque)


class PriorityTaskQueue(TaskQueue):
    """
    数值越大优先级越高。
    """

    def __init__(self) -> None:
        self._heap: list[_PriorityItem] = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._removed: set[str] = set()

    def push(
        self,
        task_id: str,
        *,
        priority: int = 0,
        enqueued_at: float = 0.0,
    ) -> None:

        item = _PriorityItem(
            sort_key=(-priority, enqueued_at, task_id),
            task_id=task_id,
        )

        with self._not_empty:
            heapq.heappush(self._heap, item)
            self._not_empty.notify()

    def pop(self, timeout: float | None = None) -> str | None:

        with self._not_empty:
            while True:
                if not self._heap:
                    if timeout is None:
                        self._not_empty.wait()
                    elif not self._not_empty.wait(timeout=timeout):
                        return None

                if not self._heap:
                    return None

                item = heapq.heappop(self._heap)
                task_id = item.task_id

                if task_id in self._removed:
                    self._removed.discard(task_id)
                    continue

                return task_id

    def remove(self, task_id: str) -> bool:

        with self._lock:
            self._removed.add(task_id)
            return True

    def qsize(self) -> int:

        with self._lock:
            return len(self._heap)


def create_task_queue(policy: QueuePolicy) -> TaskQueue:

    if policy == QueuePolicy.PRIORITY:
        return PriorityTaskQueue()

    return FIFOQueue()
