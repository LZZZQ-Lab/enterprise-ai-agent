"""
插件加载与激活（Task 6.6）。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Iterable

from app.agents.registry import AgentRegistry
from app.agents.registry import registry as default_agent_registry
from app.plugins.base import BasePlugin
from app.plugins.base import PluginContext
from app.plugins.registry import PluginRegistry
from app.plugins.registry import default_plugin_registry
from app.workflow.registry import WorkflowRegistry
from app.workflow.registry import default_workflow_registry


class PluginLoader:
    """
    发现并激活插件，无需修改 Agent / Tool / Workflow 核心实现。
    """

    def __init__(
        self,
        *,
        plugin_registry: PluginRegistry | None = None,
        agent_registry: AgentRegistry | None = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        self._plugin_registry = plugin_registry or default_plugin_registry
        self._agent_registry = agent_registry or default_agent_registry
        self._workflow_registry = (
            workflow_registry or default_workflow_registry
        )

    @property
    def plugin_registry(self) -> PluginRegistry:
        return self._plugin_registry

    def discover_package(self, package_name: str) -> list[BasePlugin]:
        """
        扫描包内模块，收集 ``PLUGIN`` 或 ``get_plugin()`` 导出。
        """

        plugins: list[BasePlugin] = []

        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return plugins

        if hasattr(package, "get_plugins"):
            exported = package.get_plugins()

            if isinstance(exported, BasePlugin):
                plugins.append(exported)
            elif isinstance(exported, Iterable):
                plugins.extend(
                    item for item in exported if isinstance(item, BasePlugin)
                )

            return plugins

        path = getattr(package, "__path__", None)

        if path is None:
            return plugins

        prefix = package.__name__ + "."

        for module_info in pkgutil.iter_modules(path, prefix):
            module = importlib.import_module(module_info.name)
            plugin = self._extract_plugin(module)

            if plugin is not None:
                plugins.append(plugin)

        return plugins

    def register_plugins(self, plugins: list[BasePlugin]) -> None:
        for plugin in plugins:
            self._plugin_registry.add(plugin, overwrite=True)

    def activate(
        self,
        plugins: list[BasePlugin] | None = None,
        *,
        plugin_ids: list[str] | None = None,
    ) -> list[str]:
        """
        执行 ``register(context)``，返回已激活 plugin_id 列表。
        """

        context = PluginContext(
            agent_registry=self._agent_registry,
            workflow_registry=self._workflow_registry,
        )

        activated: list[str] = []

        if plugins is not None:
            targets = plugins
        elif plugin_ids is not None:
            targets = [
                self._plugin_registry.get(pid).plugin for pid in plugin_ids
            ]
        else:
            targets = [
                self._plugin_registry.get(pid).plugin
                for pid in self._plugin_registry.plugin_ids()
            ]

        for plugin in targets:
            plugin.register(context)
            plugin.on_loaded(self._plugin_registry)
            self._plugin_registry.mark_active(plugin.metadata.plugin_id)
            activated.append(plugin.metadata.plugin_id)

        return activated

    def load_and_activate_builtin(self) -> list[str]:
        discovered = self.discover_package("app.plugins.builtin")
        self.register_plugins(discovered)
        return self.activate(discovered)

    @staticmethod
    def _extract_plugin(module) -> BasePlugin | None:
        if hasattr(module, "PLUGIN") and isinstance(module.PLUGIN, BasePlugin):
            return module.PLUGIN

        if hasattr(module, "get_plugin"):
            plugin = module.get_plugin()

            if isinstance(plugin, BasePlugin):
                return plugin

        return None


def bootstrap_enterprise_plugins(
    *,
    loader: PluginLoader | None = None,
) -> list[str]:
    """
    应用入口可选调用：加载并激活内置示例插件。
    """

    instance = loader or PluginLoader()
    return instance.load_and_activate_builtin()
