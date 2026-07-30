"""
Model Registry 管理器：动态加载、注册与解析。
"""

from __future__ import annotations

import threading
from pathlib import Path

from app.model_registry.loader import DEFAULT_MODELS_FILE
from app.model_registry.loader import load_into_repository
from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor
from app.model_registry.repository import ModelRegistryRepository

_manager_lock = threading.Lock()
_default_manager: ModelRegistryManager | None = None


class ModelRegistryManager:
    """
    企业模型目录统一入口。LLM Provider 通过本类获取 ModelInfo。
    """

    def __init__(
        self,
        repository: ModelRegistryRepository | None = None,
        *,
        registry_path: Path | str | None = None,
        auto_load: bool = True,
    ) -> None:
        self._repository = repository or ModelRegistryRepository()
        self._registry_path = Path(
            registry_path or DEFAULT_MODELS_FILE,
        )
        self._loaded_path: Path | None = None

        if auto_load:
            self.load_from_file(self._registry_path)

    @property
    def repository(self) -> ModelRegistryRepository:
        return self._repository

    @property
    def registry_path(self) -> Path:
        return self._registry_path

    def set_registry_path(self, path: Path | str) -> None:
        self._registry_path = Path(path)

    def load_from_file(
        self,
        path: Path | str | None = None,
        *,
        overwrite: bool = True,
    ) -> int:
        """
        从 YAML 动态加载（可重复调用以热更新）。
        """

        target = Path(path) if path is not None else self._registry_path
        count = load_into_repository(
            self._repository,
            target,
            overwrite=overwrite,
        )
        self._loaded_path = target
        return count

    def register(
        self,
        model: ModelInfo,
        *,
        overwrite: bool = False,
    ) -> None:
        self._repository.register(model, overwrite=overwrite)

    def unregister(self, name: str) -> None:
        self._repository.unregister(name)

    def get(self, name: str) -> ModelInfo:
        return self._repository.get(name)

    def resolve(self, name_or_alias: str) -> ModelInfo:
        return self._repository.resolve(name_or_alias)

    def resolve_model_id(self, name_or_alias: str) -> str:
        """
        返回推理 API 使用的 model_id。
        """

        return self.resolve(name_or_alias).model_id

    def list_models(
        self,
        *,
        provider: ModelVendor | str | None = None,
        capability: str | None = None,
    ) -> list[ModelInfo]:
        vendor: ModelVendor | None = None
        if provider is not None:
            if isinstance(provider, ModelVendor):
                vendor = provider
            else:
                vendor = ModelVendor(provider.strip().lower())
        return self._repository.list_models(
            provider=vendor,
            capability=capability,
        )

    def query(
        self,
        *,
        provider: ModelVendor | str | None = None,
        capability: str | None = None,
        name_prefix: str | None = None,
    ) -> list[ModelInfo]:
        """
        组合查询模型列表。
        """

        items = self.list_models(
            provider=provider,
            capability=capability,
        )
        if name_prefix:
            prefix = name_prefix.strip().lower()
            items = [
                m
                for m in items
                if m.name.lower().startswith(prefix)
                or m.model_id.lower().startswith(prefix)
            ]
        return items


def get_model_registry_manager() -> ModelRegistryManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            path = _resolve_registry_path_from_settings()
            _default_manager = ModelRegistryManager(
                registry_path=path,
                auto_load=True,
            )
        return _default_manager


def reset_model_registry_manager() -> None:
    global _default_manager

    with _manager_lock:
        _default_manager = None


def _resolve_registry_path_from_settings() -> Path:
    try:
        from app.config.settings import get_settings

        custom = get_settings().MODEL_REGISTRY_PATH.strip()
        if custom:
            return Path(custom)
    except Exception:
        pass
    return DEFAULT_MODELS_FILE
