from abc import ABC
from abc import abstractmethod

from app.config import AgentConfig
from app.agents.executor.plan.types import Plan
from app.agents.executor.plan.types import PlanStep
from app.agents.executor.plan.types import PlanStatus


class PlannerStrategy(ABC):
    """
    Planner 策略抽象。

    预留 RePlan、Reflection、Tree Search 等扩展。
    """

    @abstractmethod
    def build_plan(
        self,
        goal: str,
        raw_steps: list[dict],
        config: AgentConfig,
    ) -> Plan:
        pass


class SinglePlanStrategy(PlannerStrategy):
    """
    默认策略：生成单次顺序计划。
    """

    def build_plan(
        self,
        goal: str,
        raw_steps: list[dict],
        config: AgentConfig,
    ) -> Plan:

        steps: list[PlanStep] = []

        for index, item in enumerate(
            raw_steps[: config.max_plan_steps],
            start=1,
        ):

            steps.append(
                PlanStep(
                    id=str(
                        item.get(
                            "id",
                            f"step-{index}",
                        )
                    ),
                    description=str(
                        item.get(
                            "description",
                            goal,
                        )
                    ),
                    tool=item.get("tool"),
                )
            )

        if not steps:

            steps.append(
                PlanStep(
                    id="step-1",
                    description=goal,
                )
            )

        return Plan(
            goal=goal,
            steps=steps,
            status=PlanStatus.PENDING,
            metadata={
                "strategy": "single_plan",
            },
        )
