from app.core.logger import logger
from app.llm.exceptions import LLMException
from app.memory.exceptions import MemoryError
from app.tools.types import ToolResult


class AgentErrorHandler:
    """
    统一处理 Agent Runtime 中的异常。
    """

    def handle_llm_error(
        self,
        error: Exception,
    ):

        from app.agents.types import AgentResult

        logger.error(
            "LLM error: %s",
            error
        )

        if isinstance(error, LLMException):

            message = f"LLM service error: {error}"

        else:

            message = f"Unexpected LLM error: {error}"

        return AgentResult(
            success=False,
            model="",
            content=message,
        )

    def handle_tool_error(
        self,
        error: Exception,
        tool_name: str,
    ) -> ToolResult:

        logger.error(
            "Tool '%s' error: %s",
            tool_name,
            error,
        )

        return ToolResult(
            success=False,
            content=str(error),
        )

    def handle_memory_error(
        self,
        error: Exception,
    ):

        from app.agents.types import AgentResult

        logger.error(
            "Memory error: %s",
            error,
        )

        if isinstance(error, MemoryError):

            message = f"Memory error: {error}"

        else:

            message = f"Unexpected memory error: {error}"

        return AgentResult(
            success=False,
            model="",
            content=message,
        )
