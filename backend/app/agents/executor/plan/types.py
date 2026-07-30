from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class PlanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """
    计划中的单个执行步骤。
    """

    id: str

    description: str

    tool: str | None = None

    status: StepStatus = StepStatus.PENDING

    result: str = ""


@dataclass
class Plan:
    """
    Agent 执行计划。
    """

    goal: str

    steps: list[PlanStep] = field(
        default_factory=list
    )

    status: PlanStatus = PlanStatus.PENDING

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class PlanResult:
    """
    Workflow 执行结果。
    """

    plan: Plan

    success: bool

    content: str

    model: str = ""
