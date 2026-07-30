from typing import TYPE_CHECKING

from app.config import AgentConfig
from app.agents.executor.plan.error_handler import WorkflowAction
from app.agents.executor.plan.error_handler import WorkflowErrorHandler
from app.agents.executor.plan.types import Plan
from app.agents.executor.plan.types import PlanStatus
from app.agents.executor.plan.types import StepStatus
from app.agents.executor.plan.workflow_base import Workflow
from app.tools.manager import ToolManager
from app.tools.types import ToolContext

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult
    from app.llm.types import Message
    from app.agents.executor.agent_executor import AgentExecutor
    from app.prompts.builder import PromptBuilder
    from app.agents.executor.tracer import AgentTracer


class StepExecutor:
    """
    单步执行器。

    负责执行单个 PlanStep，可调用 Tool / LLM / MCP Tool。
    WorkflowExecutor 不直接处理执行细节。
    """

    def __init__(
        self,
        agent_executor: "AgentExecutor",
        tool_manager: ToolManager,
        prompt_builder: "PromptBuilder",
        config: AgentConfig,
        tracer: "AgentTracer | None" = None,
        error_handler: WorkflowErrorHandler | None = None,
    ):

        self._agent_executor = agent_executor
        self._tool_manager = tool_manager
        self._prompt_builder = prompt_builder
        self._config = config
        self._tracer = tracer
        self._error_handler = (
            error_handler or WorkflowErrorHandler()
        )

    def execute(
        self,
        step,
        context: "AgentContext",
        plan: Plan,
        base_messages: list["Message"],
        completed_steps: list,
    ) -> "AgentResult":

        from app.agents.types import AgentResult

        step.status = StepStatus.RUNNING

        if self._tracer is not None:

            self._tracer.on_plan_step_start(
                plan,
                step,
            )

        if step.tool:

            tool_result = self._tool_manager.execute(

                ToolContext(
                    tool_name=step.tool,
                    arguments={},
                )

            )

            action = self._error_handler.handle_tool_failure(
                step,
                tool_result,
            )

            if not tool_result.success:

                if action == WorkflowAction.ABORT:

                    step.status = StepStatus.FAILED

                    return AgentResult(
                        success=False,
                        model="",
                        content=step.result,
                    )

                step.status = StepStatus.SKIPPED

                if self._tracer is not None:

                    self._tracer.on_plan_step_result(
                        plan,
                        step,
                    )

                return AgentResult(
                    success=False,
                    model="",
                    content=step.result,
                )

            step.result = tool_result.content
            step.status = StepStatus.COMPLETED

            if self._tracer is not None:

                self._tracer.on_plan_step_result(
                    plan,
                    step,
                )

            return AgentResult(
                success=True,
                model="",
                content=step.result,
            )

        context.plan = plan
        context.current_step = step

        messages = self._prompt_builder.build(
            context,
            completed_steps=completed_steps,
        )

        step_context = self._build_step_context(
            context,
            step,
        )

        result = self._agent_executor.run(
            step_context,
            messages,
        )

        step.result = result.content or ""
        step.status = (
            StepStatus.COMPLETED
            if result.success
            else StepStatus.FAILED
        )

        if self._tracer is not None:

            self._tracer.on_plan_step_result(
                plan,
                step,
            )

        return result

    def synthesize(
        self,
        plan: Plan,
        context: "AgentContext",
        base_messages: list["Message"],
    ) -> "AgentResult":

        from app.agents.types import AgentContext as AC
        from app.llm.types import Message

        completed = [
            step
            for step in plan.steps
            if step.status == StepStatus.COMPLETED
            and step.result
        ]

        if len(completed) == 1:

            step = completed[0]

            return AgentResult(
                success=True,
                model="",
                content=step.result,
            )

        summary_lines = [
            f"- {step.description}: {step.result}"
            for step in completed
        ]

        synthesis_context = AC(
            session_id=context.session_id,
            user_message=(
                "Based on the completed plan steps below, "
                "provide a final consolidated answer for "
                f"the goal: {plan.goal}\n\n"
                + "\n".join(summary_lines)
            ),
            history=context.history,
        )

        messages = list(base_messages)
        messages.append(
            Message(
                role="user",
                content=synthesis_context.user_message,
            )
        )

        return self._agent_executor.run(
            synthesis_context,
            messages,
        )

    @staticmethod
    def _build_step_context(
        context: "AgentContext",
        step,
    ):

        from app.agents.types import AgentContext as AC

        return AC(
            session_id=context.session_id,
            user_message=(
                f"Current step: {step.description}\n"
                f"Overall goal: {context.user_message}"
            ),
            history=context.history,
            plan=context.plan,
            current_step=step,
        )
