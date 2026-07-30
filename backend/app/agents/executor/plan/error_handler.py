from enum import Enum

from app.core.logger import logger
from app.agents.executor.plan.types import Plan
from app.agents.executor.plan.types import PlanStatus
from app.agents.executor.plan.types import PlanStep
from app.agents.executor.plan.types import StepStatus
from app.tools.types import ToolResult


class WorkflowAction(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class WorkflowErrorHandler:
    """
    统一处理 Workflow / Step 异常。

    支持重试、跳过、中止，避免异常散落业务代码。
    """

    def handle_step_failure(
        self,
        step: PlanStep,
        error: Exception,
        retry_count: int,
        max_retries: int,
    ) -> WorkflowAction:

        logger.error(
            "Workflow step '%s' failed (retry %d/%d): %s",
            step.id,
            retry_count,
            max_retries,
            error,
        )

        if retry_count < max_retries:

            return WorkflowAction.RETRY

        return WorkflowAction.SKIP

    def handle_tool_failure(
        self,
        step: PlanStep,
        tool_result: ToolResult,
    ) -> WorkflowAction:

        if tool_result.success:

            return WorkflowAction.SKIP

        logger.error(
            "Workflow step '%s' tool failed: %s",
            step.id,
            tool_result.content,
        )

        step.result = tool_result.content
        step.status = StepStatus.FAILED

        return WorkflowAction.SKIP

    def handle_abort(
        self,
        plan: Plan,
        reason: str,
    ) -> None:

        logger.error(
            "Workflow aborted: %s",
            reason,
        )

        plan.status = PlanStatus.ABORTED

    def handle_plan_failure(
        self,
        plan: Plan,
        error: Exception,
    ) -> None:

        logger.error(
            "Workflow plan failed: %s",
            error,
        )

        plan.status = PlanStatus.FAILED
