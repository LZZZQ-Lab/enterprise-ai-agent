"""Task 6.2 Agent Scheduler tests."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.scheduler.queue import QueuePolicy
from app.scheduler.queue import TaskStatus
from app.scheduler.scheduler import AgentScheduler

_flaky_attempts = 0
_flaky_lock = threading.Lock()


class _SlowEchoAgent(BaseAgent):
    def __init__(self, delay: float = 0.0, **kwargs: Any) -> None:
        super().__init__()
        self._delay = delay

    @property
    def name(self) -> str:
        return "echo"

    def get_capabilities(self) -> list[str]:
        return ["echo"]

    def execute(self, context: AgentContext) -> AgentResult:
        if self._delay:
            time.sleep(self._delay)
        return AgentResult(
            success=True,
            model="mock",
            content=f"echo:{context.user_message}",
        )


class _FlakyAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "flaky"

    def get_capabilities(self) -> list[str]:
        return ["flaky"]

    def execute(self, context: AgentContext) -> AgentResult:
        global _flaky_attempts
        with _flaky_lock:
            _flaky_attempts += 1
            attempt = _flaky_attempts
        if attempt == 1:
            return AgentResult(success=False, model="mock", content="fail once")
        return AgentResult(
            success=True,
            model="mock",
            content=f"ok:{context.user_message}",
        )


class _HangAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "hang"

    def get_capabilities(self) -> list[str]:
        return ["hang"]

    def execute(self, context: AgentContext) -> AgentResult:
        time.sleep(2.0)
        return AgentResult(success=True, model="mock", content="late")


def _runtime_with_agent(
    agent_cls: type[BaseAgent],
    *,
    policy: QueuePolicy = QueuePolicy.FIFO,
) -> AgentRuntime:
    reg = AgentRegistry()
    reg.register("echo", agent_cls)
    reg.register("flaky", agent_cls)
    reg.register("hang", agent_cls)

    scheduler = AgentScheduler(policy=policy, worker_count=1, auto_start=True)
    runtime = AgentRuntime(registry=reg, default_agent="echo", scheduler=scheduler)
    scheduler.set_executor(runtime.execute_task)
    return runtime


def test_runtime_routes_through_scheduler() -> None:
    runtime = _runtime_with_agent(_SlowEchoAgent)

    result = runtime.run(
        AgentTask(session_id="s", user_message="hi", agent_name="echo"),
    )

    assert result.success is True
    assert result.content == "echo:hi"


def test_fifo_order_under_concurrency() -> None:
    order: list[str] = []
    lock = threading.Lock()

    class _OrderAgent(BaseAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()

        @property
        def name(self) -> str:
            return "echo"

        def get_capabilities(self) -> list[str]:
            return ["echo"]

        def execute(self, context: AgentContext) -> AgentResult:
            time.sleep(0.05)
            with lock:
                order.append(context.user_message)
            return AgentResult(success=True, model="m", content=context.user_message)

    runtime = _runtime_with_agent(_OrderAgent, policy=QueuePolicy.FIFO)
    scheduler = runtime._scheduler

    assert scheduler is not None

    ids = [
        scheduler.submit(
            AgentTask(session_id="s", user_message=f"m{i}", agent_name="echo"),
        )
        for i in range(4)
    ]

    deadline = time.time() + 10.0

    while time.time() < deadline:
        if all(
            scheduler.get_record(tid).status
            in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.TIMEOUT)
            for tid in ids
        ):
            break
        time.sleep(0.05)

    assert order == ["m0", "m1", "m2", "m3"]


def test_priority_queue_runs_high_first() -> None:
    finished: list[str] = []
    lock = threading.Lock()
    gate = threading.Event()

    class _PriorityAgent(BaseAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()

        @property
        def name(self) -> str:
            return "echo"

        def get_capabilities(self) -> list[str]:
            return ["echo"]

        def execute(self, context: AgentContext) -> AgentResult:
            gate.wait(timeout=5.0)
            with lock:
                finished.append(context.user_message)
            return AgentResult(success=True, model="m", content="ok")

    runtime = _runtime_with_agent(_PriorityAgent, policy=QueuePolicy.PRIORITY)
    scheduler = runtime._scheduler
    assert scheduler is not None

    low = scheduler.submit(
        AgentTask(session_id="s", user_message="low", agent_name="echo"),
        priority=1,
    )
    high = scheduler.submit(
        AgentTask(session_id="s", user_message="high", agent_name="echo"),
        priority=100,
    )
    mid = scheduler.submit(
        AgentTask(session_id="s", user_message="mid", agent_name="echo"),
        priority=50,
    )

    time.sleep(0.2)
    gate.set()

    deadline = time.time() + 10.0
    for tid in (low, high, mid):
        while time.time() < deadline:
            rec = scheduler.get_record(tid)
            assert rec is not None
            if rec.status == TaskStatus.SUCCESS:
                break
            time.sleep(0.05)

    assert finished[0] == "high"
    assert "low" in finished


def test_retry_after_agent_failure() -> None:
    global _flaky_attempts
    with _flaky_lock:
        _flaky_attempts = 0

    runtime = _runtime_with_agent(_FlakyAgent)
    scheduler = runtime._scheduler
    assert scheduler is not None

    result = scheduler.submit_and_wait(
        AgentTask(session_id="s", user_message="x", agent_name="flaky"),
        max_retries=1,
    )

    assert result.success is True
    assert result.content == "ok:x"


def test_timeout_marks_task_timeout() -> None:
    runtime = _runtime_with_agent(_HangAgent)
    scheduler = runtime._scheduler
    assert scheduler is not None

    task_id = scheduler.submit(
        AgentTask(session_id="s", user_message="wait", agent_name="hang"),
        timeout_sec=0.3,
        max_retries=0,
    )

    deadline = time.time() + 5.0
    while time.time() < deadline:
        rec = scheduler.get_record(task_id)
        assert rec is not None
        if rec.status == TaskStatus.TIMEOUT:
            break
        time.sleep(0.05)
    else:
        pytest.fail("expected TIMEOUT status")

    rec = scheduler.get_record(task_id)
    assert rec is not None
    assert rec.status == TaskStatus.TIMEOUT


def test_cancel_pending_task() -> None:
    blocker = threading.Event()

    class _BlockAgent(BaseAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()

        @property
        def name(self) -> str:
            return "echo"

        def get_capabilities(self) -> list[str]:
            return ["echo"]

        def execute(self, context: AgentContext) -> AgentResult:
            blocker.wait(timeout=5.0)
            return AgentResult(success=True, model="m", content="done")

    runtime = _runtime_with_agent(_BlockAgent)
    scheduler = runtime._scheduler
    assert scheduler is not None

    first = scheduler.submit(
        AgentTask(session_id="s", user_message="block", agent_name="echo"),
    )
    time.sleep(0.05)

    pending = scheduler.submit(
        AgentTask(session_id="s", user_message="cancel-me", agent_name="echo"),
    )

    assert scheduler.cancel(pending) is True
    rec = scheduler.get_record(pending)
    assert rec is not None
    assert rec.status == TaskStatus.CANCELLED

    blocker.set()
    deadline = time.time() + 5.0
    while time.time() < deadline:
        rec_first = scheduler.get_record(first)
        assert rec_first is not None
        if rec_first.status == TaskStatus.SUCCESS:
            break
        time.sleep(0.05)
