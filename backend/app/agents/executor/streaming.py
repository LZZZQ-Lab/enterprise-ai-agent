from abc import ABC
from abc import abstractmethod

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.agents.types import AgentResult


class StreamingAgent(ABC):
    """
    流式 Agent 接口（预留，T7.9 不实现具体逻辑）。
    """

    @abstractmethod
    def stream_execute(
        self,
        context: "AgentContext",
    ):
        pass


class StreamingExecutor(ABC):
    """
    流式执行器接口（预留，T7.9 不实现具体逻辑）。
    """

    @abstractmethod
    def stream(
        self,
        context: "AgentContext",
    ):
        pass
