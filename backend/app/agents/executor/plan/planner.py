from abc import ABC
from abc import abstractmethod

from typing import TYPE_CHECKING

from app.agents.executor.plan.types import Plan

if TYPE_CHECKING:
    from app.agents.types import AgentContext


class Planner(ABC):
    """
    Agent 规划器抽象。

    根据用户目标生成 Plan，与 Plan-and-Execute 流程对接。
    后续可替换为 RePlan、Reflection、Tree Search 等策略。
    """

    @abstractmethod
    def plan(
        self,
        context: "AgentContext",
    ) -> Plan:
        pass


class NoPlanner(Planner):
    """
    默认 Planner：返回单步计划，等效于直接 ReAct。
    """

    def plan(
        self,
        context: "AgentContext",
    ) -> Plan:

        from app.agents.executor.plan.types import PlanStep
        from app.agents.executor.plan.types import PlanStatus

        return Plan(
            goal=context.user_message,
            steps=[
                PlanStep(
                    id="step-1",
                    description=context.user_message,
                )
            ],
            status=PlanStatus.PENDING,
        )
