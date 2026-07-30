"""兼容层：请改用 app.agents.executor.plan.workflow_executor。"""

from app.agents.executor.plan.workflow_executor import WorkflowExecutor

__all__ = ['WorkflowExecutor']
