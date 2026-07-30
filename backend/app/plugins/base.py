"""
企业插件基类（Task 6.6）。
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import TYPE_CHECKING
from typing import Type

if TYPE_CHECKING:
    from app.agents.base import BaseAgent
    from app.agents.registry import AgentRegistry
    from app.plugins.registry import PluginRegistry
    from app.tools.base_tool import BaseTool
    from app.workflow.graph import WorkflowGraph
    from app.workflow.registry import WorkflowRegistry


class PluginKind(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    WORKFLOW = "workflow"


@dataclass(frozen=True)
class PluginMetadata:
    plugin_id: str
    name: str
    version: str
    kind: PluginKind
    description: str = ""
    author: str = ""
    tags: tuple[str, ...] = ()


@dataclass
class PluginContext:
    """
    插件注册上下文（注入平台 Registry，无需改核心代码）。
    """

    agent_registry: AgentRegistry
    workflow_registry: WorkflowRegistry
    extra: dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """插件抽象基类。"""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        raise NotImplementedError

    @abstractmethod
    def register(self, context: PluginContext) -> None:
        """
        将 Agent / Tool / Workflow 注册到平台。
        """

    def on_loaded(self, plugin_registry: PluginRegistry) -> None:
        """可选：加载后回调。"""


class AgentPlugin(BasePlugin):
    """Agent 插件：注册 Agent 类型。"""

    kind = PluginKind.AGENT

    @abstractmethod
    def agent_class(self) -> Type[BaseAgent]:
        raise NotImplementedError

    @abstractmethod
    def agent_name(self) -> str:
        raise NotImplementedError

    def register(self, context: PluginContext) -> None:
        context.agent_registry.register(
            self.agent_name(),
            self.agent_class(),
        )


class ToolPlugin(BasePlugin):
    """Tool 插件：注册 Tool 实例。"""

    kind = PluginKind.TOOL

    @abstractmethod
    def tool(self) -> BaseTool:
        raise NotImplementedError

    def register(self, context: PluginContext) -> None:
        from app.tools.registry import ToolRegistry

        ToolRegistry.register(self.tool())


class WorkflowPlugin(BasePlugin):
    """Workflow 插件：注册 WorkflowGraph。"""

    kind = PluginKind.WORKFLOW

    @abstractmethod
    def workflow(self) -> WorkflowGraph:
        raise NotImplementedError

    def register(self, context: PluginContext) -> None:
        context.workflow_registry.register(
            self.workflow(),
            overwrite=True,
        )
