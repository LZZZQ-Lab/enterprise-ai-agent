"""兼容层：请改用 app.agents.executor.workflow。"""

from app.agents.executor.workflow import SequentialWorkflow
from app.agents.executor.workflow import Workflow

__all__ = ["SequentialWorkflow", "Workflow"]
