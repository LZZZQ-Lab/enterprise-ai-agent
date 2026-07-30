from abc import ABC
from abc import abstractmethod
from typing import Any

from app.mcp.types import MCPPromptDefinition
from app.mcp.types import MCPPromptResult
from app.mcp.types import MCPResourceContent
from app.mcp.types import MCPResourceInfo
from app.mcp.types import MCPToolCallResult
from app.mcp.types import MCPToolDefinition


class MCPClient(ABC):
    """
    MCP Client 抽象接口。
    """

    @property
    @abstractmethod
    def server_name(self) -> str:

        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:

        pass

    @abstractmethod
    def connect(self) -> None:

        pass

    @abstractmethod
    def disconnect(self) -> None:

        pass

    @abstractmethod
    def list_tools(self) -> list[MCPToolDefinition]:

        pass

    @abstractmethod
    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:

        pass

    @abstractmethod
    def list_resources(self) -> list[MCPResourceInfo]:

        pass

    @abstractmethod
    def read_resource(
        self,
        uri: str,
    ) -> MCPResourceContent:

        pass

    @abstractmethod
    def list_prompts(self) -> list[MCPPromptDefinition]:

        pass

    @abstractmethod
    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPPromptResult:

        pass
