from typing import TYPE_CHECKING

from app.config import AgentConfig
from app.agents.executor.plan.error_handler import WorkflowErrorHandler
from app.agents.executor.plan.planner import Planner
from app.agents.executor.plan.step_executor import StepExecutor
from app.agents.executor.plan.types import Plan
from app.agents.executor.plan.workflow_base import Workflow

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult
    from app.llm.types import Message
    from app.agents.executor.agent_executor import AgentExecutor
    from app.agents.executor.tracer import AgentTracer


class WorkflowExecutor:
    """
    Workflow 执行器。

    负责 Planner → Workflow → Agent Loop 编排。
    enable_planner=False 时退化为原有 Agent Loop。
    """

    def __init__(
        self,
        config: AgentConfig,
        planner: Planner,
        workflow: Workflow,
        step_executor: StepExecutor,
        agent_executor: "AgentExecutor",
        tracer: "AgentTracer | None" = None,
        error_handler: WorkflowErrorHandler | None = None,
    ):

        self._config = config
        self._planner = planner
        self._workflow = workflow
        self._step_executor = step_executor
        self._agent_executor = agent_executor
        self._tracer = tracer
        self._error_handler = (
            error_handler or WorkflowErrorHandler()
        )

    def run(
        self,
        context: "AgentContext",
        base_messages: list["Message"],
    ) -> "AgentResult":

        if not self._config.enable_planner:

            return self._agent_executor.run(
                context,
                base_messages,
            )

        try:

            plan = self._planner.plan(context)

        except Exception as error:

            self._error_handler.handle_plan_failure(
                Plan(goal=context.user_message),
                error,
            )

            return self._agent_executor.run(
                context,
                base_messages,
            )

        context.plan = plan

        if self._tracer is not None:

            self._tracer.on_plan_created(plan)

            self._tracer.on_workflow_start(
                self._config.workflow_mode,
            )

        return self._workflow.run(
            plan,
            context,
            self._step_executor,
            base_messages,
        )
