"""
Phase 5.1：AI 软件团队 Task 模型。
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


def _new_task_id() -> str:

    return uuid4().hex[:12]


@dataclass
class SoftwareTeamTask:
    """
    PM 分配给专职 Agent 的工作项。
    """

    title: str
    description: str
    agent: str
    id: str = field(default_factory=_new_task_id)
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""

    def to_dict(self) -> dict[str, Any]:

        payload = asdict(self)
        payload["status"] = self.status.value

        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoftwareTeamTask:

        status = data.get("status", TaskStatus.PENDING)

        if isinstance(status, str):

            status = TaskStatus(status)

        return cls(
            id=str(data.get("id") or _new_task_id()),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            agent=str(data.get("agent", "")),
            status=status,
            result=str(data.get("result", "")),
        )


@dataclass
class SoftwareProject:
    """
    PM 创建的项目上下文。
    """

    requirement: str
    goal_summary: str
    name: str = ""
    id: str = field(default_factory=_new_task_id)
    tasks: list[SoftwareTeamTask] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:

        return {
            "id": self.id,
            "name": self.name,
            "requirement": self.requirement,
            "goal_summary": self.goal_summary,
            "tasks": [task.to_dict() for task in self.tasks],
        }
