from typing import TYPE_CHECKING

from app.config import AgentConfig
from app.agents.executor.plan.error_handler import WorkflowAction
from app.agents.executor.plan.error_handler import WorkflowErrorHandler
from app.agents.executor.plan.types import PlanStatus
from app.agents.executor.plan.types import StepStatus
from app.agents.executor.plan.workflow_base import Workflow

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult
    from app.llm.types import Message
    from app.agents.executor.plan.step_executor import StepExecutor
    from app.agents.executor.tracer import AgentTracer


class SequentialWorkflow(Workflow):
    """
    顺序 Workflow：逐步执行 PlanStep。
    """

    def __init__(
        self,
        config: AgentConfig,
        error_handler: WorkflowErrorHandler | None = None,
        tracer: "AgentTracer | None" = None,
    ):

        self._config = config
        self._error_handler = (
            error_handler or WorkflowErrorHandler()
        )
        self._tracer = tracer

    def run(
        self,
        plan,
        context: "AgentContext",
        step_executor: "StepExecutor",
        base_messages: list["Message"],
    ) -> "AgentResult":

        from app.agents.types import AgentResult

        plan.status = PlanStatus.RUNNING

        completed_steps = []
        last_result = None
        max_retries = self._config.step_max_retries

        for step in plan.steps[
            : self._config.max_plan_steps
        ]:

            retry_count = 0

            while True:

                try:

                    last_result = step_executor.execute(
                        step,
                        context,
                        plan,
                        base_messages,
                        completed_steps,
                    )

                    if step.status == StepStatus.COMPLETED:

                        completed_steps.append(step)
                        break

                    if step.status == StepStatus.SKIPPED:

                        break

                    action = self._error_handler.handle_step_failure(
                        step,
                        Exception(step.result or "step failed"),
                        retry_count,
                        max_retries,
                    )

                except Exception as error:

                    action = self._error_handler.handle_step_failure(
                        step,
                        error,
                        retry_count,
                        max_retries,
                    )

                if action == WorkflowAction.RETRY:

                    retry_count += 1
                    continue

                if action == WorkflowAction.SKIP:

                    step.status = StepStatus.SKIPPED
                    break

                if action == WorkflowAction.ABORT:

                    self._error_handler.handle_abort(
                        plan,
                        f"Step '{step.id}' aborted.",
                    )

                    return AgentResult(
                        success=False,
                        model=getattr(
                            last_result,
                            "model",
                            "",
                        ),
                        content=step.result or "Workflow aborted.",
                    )

            if plan.status == PlanStatus.ABORTED:

                break

        if not completed_steps:

            plan.status = PlanStatus.FAILED

            return AgentResult(
                success=False,
                model="",
                content="No plan steps completed successfully.",
            )

        final_result = step_executor.synthesize(
            plan,
            context,
            base_messages,
        )

        plan.status = (
            PlanStatus.COMPLETED
            if final_result.success
            else PlanStatus.FAILED
        )

        if self._tracer is not None:

            self._tracer.on_plan_complete(plan)

        return final_result
