"""
Task 6.2 Agent Scheduler Demo。

演示：
- 多 Agent 异步入队
- FIFO 与 Priority 两种策略
- 通过 AgentRuntime.run（统一经 Scheduler 执行）

运行:
    cd backend
    python -m applications.scheduler.run_scheduler_demo
"""

from __future__ import annotations

import threading
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.scheduler.queue import QueuePolicy
from app.scheduler.queue import TaskStatus
from app.scheduler.scheduler import AgentScheduler


class DemoAgent(BaseAgent):
    """按 agent_name 区分角色，模拟不同 Agent 耗时。"""

    def __init__(self, label: str = "", **kwargs) -> None:
        super().__init__()
        self._label = label

    @property
    def name(self) -> str:
        return self._label or "demo"

    def get_capabilities(self) -> list[str]:
        return ["demo"]

    def execute(self, context: AgentContext) -> AgentResult:
        role = context.agent_name or "demo"
        delay = {"product": 0.15, "architecture": 0.1, "developer": 0.2}.get(
            role,
            0.05,
        )
        time.sleep(delay)
        body = f"[{role}] done: {context.user_message[:40]}"
        print(f"  worker finished {body}")
        return AgentResult(success=True, model="demo", content=body)


def _build_runtime(policy: QueuePolicy) -> tuple[AgentRuntime, AgentScheduler]:
    reg = AgentRegistry()

    class ProductDemo(DemoAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(label="product", **kwargs)

    class ArchitectureDemo(DemoAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(label="architecture", **kwargs)

    class DeveloperDemo(DemoAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(label="developer", **kwargs)

    reg.register("product", ProductDemo)
    reg.register("architecture", ArchitectureDemo)
    reg.register("developer", DeveloperDemo)
    reg.register("demo", DemoAgent)

    scheduler = AgentScheduler(
        policy=policy,
        worker_count=3,
        auto_start=True,
    )
    runtime = AgentRuntime(
        registry=reg,
        default_agent="demo",
        scheduler=scheduler,
    )
    scheduler.set_executor(runtime.execute_task)
    return runtime, scheduler


def demo_fifo_parallel() -> None:
    print("\n=== FIFO：三 Agent 并行提交 ===")
    runtime, scheduler = _build_runtime(QueuePolicy.FIFO)
    start = time.perf_counter()

    tasks = [
        AgentTask(
            session_id="demo-fifo",
            user_message=f"task-{role}",
            agent_name=role,
        )
        for role in ("product", "architecture", "developer")
    ]

    threads: list[threading.Thread] = []
    results: list[AgentResult] = []

    def _run(task: AgentTask) -> None:
        results.append(runtime.run(task))

    for task in tasks:
        t = threading.Thread(target=_run, args=(task,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.perf_counter() - start
    print(f"  completed {len(results)} tasks in {elapsed:.2f}s (parallel)")
    for r in results:
        print(f"    -> {r.content}")


def demo_priority() -> None:
    print("\n=== Priority：低优先级先提交，高优先级先完成 ===")
    runtime, scheduler = _build_runtime(QueuePolicy.PRIORITY)
    gate = threading.Event()

    class GateProduct(DemoAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(label="product", **kwargs)

        def execute(self, context: AgentContext) -> AgentResult:
            gate.wait(timeout=10.0)
            return super().execute(context)

    class GateDeveloper(DemoAgent):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(label="developer", **kwargs)

        def execute(self, context: AgentContext) -> AgentResult:
            gate.wait(timeout=10.0)
            return super().execute(context)

    reg = runtime.registry
    reg.register("product", GateProduct)
    reg.register("developer", GateDeveloper)

    low = scheduler.submit(
        AgentTask(session_id="p", user_message="low", agent_name="product"),
        priority=1,
    )
    high = scheduler.submit(
        AgentTask(session_id="p", user_message="high", agent_name="developer"),
        priority=100,
    )

    time.sleep(0.3)
    gate.set()

    deadline = time.time() + 15.0
    while time.time() < deadline:
        h = scheduler.get_record(high)
        l = scheduler.get_record(low)
        if h and l and h.status == TaskStatus.SUCCESS and l.status == TaskStatus.SUCCESS:
            break
        time.sleep(0.05)

    print(f"  high task status: {scheduler.get_record(high).status.value}")
    print(f"  low task status: {scheduler.get_record(low).status.value}")


def main() -> None:
    print("Agent Scheduler Demo (Task 6.2)")
    demo_fifo_parallel()
    demo_priority()
    print("\nDemo finished.")


if __name__ == "__main__":
    main()
