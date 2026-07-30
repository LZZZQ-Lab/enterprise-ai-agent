"""
插件注册表（Task 6.6）。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from dataclasses import field

from app.plugins.base import BasePlugin
from app.plugins.base import PluginKind
from app.plugins.base import PluginMetadata


@dataclass
class RegisteredPlugin:
    metadata: PluginMetadata
    plugin: BasePlugin
    active: bool = False


class PluginRegistry:
    """
    已发现 / 已激活插件索引。
    """

    def __init__(self) -> None:
        self._plugins: dict[str, RegisteredPlugin] = {}
        self._lock = threading.RLock()

    def add(self, plugin: BasePlugin, *, overwrite: bool = False) -> None:
        meta = plugin.metadata
        plugin_id = meta.plugin_id

        with self._lock:
            if plugin_id in self._plugins and not overwrite:
                raise ValueError(f"Plugin already registered: {plugin_id}")

            self._plugins[plugin_id] = RegisteredPlugin(
                metadata=meta,
                plugin=plugin,
                active=False,
            )

    def mark_active(self, plugin_id: str) -> None:
        with self._lock:
            entry = self._plugins.get(plugin_id)

            if entry is None:
                raise KeyError(plugin_id)

            entry.active = True

    def get(self, plugin_id: str) -> RegisteredPlugin:
        with self._lock:
            entry = self._plugins.get(plugin_id)

            if entry is None:
                raise KeyError(f"Plugin not found: {plugin_id}")

            return entry

    def list_plugins(
        self,
        *,
        kind: PluginKind | None = None,
        active_only: bool = False,
    ) -> list[PluginMetadata]:
        with self._lock:
            items = list(self._plugins.values())

        if kind is not None:
            items = [item for item in items if item.metadata.kind == kind]

        if active_only:
            items = [item for item in items if item.active]

        return [item.metadata for item in items]

    def plugin_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._plugins.keys())


default_plugin_registry = PluginRegistry()
