"""兼容层：请改用 app.agents.executor.streaming。"""

from app.agents.executor.streaming import StreamingAgent
from app.agents.executor.streaming import StreamingExecutor

__all__ = ["StreamingAgent", "StreamingExecutor"]
