"""兼容层：请改用 app.agents.executor.plan.strategy。"""

from app.agents.executor.plan.strategy import PlannerStrategy
from app.agents.executor.plan.strategy import SinglePlanStrategy

__all__ = ['PlannerStrategy', 'SinglePlanStrategy']
