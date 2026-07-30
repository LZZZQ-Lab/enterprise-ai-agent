"""Task 8.4 stress test scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StressScenario:
    id: str
    label: str
    users: int
    spawn_rate: int
    run_time: str | None = None
    max_requests: int | None = None


SCENARIOS: tuple[StressScenario, ...] = (
    StressScenario(
        id="10_users",
        label="10 并发用户",
        users=10,
        spawn_rate=2,
        run_time="60s",
    ),
    StressScenario(
        id="100_users",
        label="100 并发用户",
        users=100,
        spawn_rate=10,
        run_time="120s",
    ),
    StressScenario(
        id="1000_requests",
        label="1000 总请求",
        users=50,
        spawn_rate=10,
        max_requests=1000,
    ),
)

QUICK_SCENARIOS: tuple[StressScenario, ...] = (
    StressScenario(
        id="10_users",
        label="10 并发用户 (quick)",
        users=3,
        spawn_rate=3,
        run_time="8s",
    ),
    StressScenario(
        id="100_users",
        label="100 并发用户 (quick)",
        users=5,
        spawn_rate=5,
        run_time="8s",
    ),
    StressScenario(
        id="1000_requests",
        label="1000 总请求 (quick)",
        users=5,
        spawn_rate=5,
        max_requests=20,
    ),
)


def get_scenarios(quick: bool = False) -> tuple[StressScenario, ...]:
    return QUICK_SCENARIOS if quick else SCENARIOS
