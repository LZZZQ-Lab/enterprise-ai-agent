"""兼容层：请改用 app.agents.executor.plan.error_handler。"""

from app.agents.executor.plan.error_handler import WorkflowErrorHandler

__all__ = ['WorkflowErrorHandler']
