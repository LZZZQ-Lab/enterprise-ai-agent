from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult
    from app.llm.types import Message
    from app.agents.executor.plan.step_executor import StepExecutor
    from app.agents.executor.plan.types import Plan


class Workflow(ABC):
    """
    Workflow 抽象：定义 Plan 的执行流程。

    不直接调用具体 Tool，由 StepExecutor 负责执行细节。
    后续可扩展 ParallelWorkflow、ConditionalWorkflow 等。
    """

    @abstractmethod
    def run(
        self,
        plan: "Plan",
        context: "AgentContext",
        step_executor: "StepExecutor",
        base_messages: list["Message"],
    ) -> "AgentResult":
        pass
