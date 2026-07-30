from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.memory.manager import MemoryManager


class BaseAgent(ABC):
    """
    企业级 Agent 标准接口。

    子类实现 execute()；run() 负责统一生命周期（before → execute → after）。
    """

    def __init__(self) -> None:

        self.memory = MemoryManager()

    @property
    def name(self) -> str:
        """
        Agent 标识，供 Registry / Runtime 路由使用。
        """

        class_name = type(self).__name__

        if class_name.endswith("Agent"):

            return class_name[: -len("Agent")].lower()

        return class_name.lower()

    def can_handle(
        self,
        task_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        判断 Agent 是否能处理该任务，Multi-Agent 路由时可覆写。
        """

        return True

    def get_capabilities(self) -> list[str]:
        """
        返回 Agent 能力标签。
        """

        return ["chat"]

    def before_run(
        self,
        context: AgentContext,
    ) -> None:
        """
        执行前钩子，子类可覆写。

        Memory 加载已由 PromptBuilder 负责，Agent 无需在此访问 Memory。
        """

    @abstractmethod
    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        """
        核心执行逻辑，子类必须实现。
        """

    def after_run(
        self,
        context: AgentContext,
        result: AgentResult,
    ) -> None:
        """
        执行后保存聊天记录。
        """

        self.memory.save_user_message(
            context.session_id,
            context.user_message,
        )

        self.memory.save_assistant_message(
            context.session_id,
            result.content,
        )

    def run(
        self,
        context: AgentContext,
    ) -> AgentResult:
        """
        Agent 标准生命周期入口。
        """

        self.before_run(context)

        result = self.execute(context)

        self.after_run(context, result)

        return result
