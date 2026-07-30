"""
Model Registry 内存仓库：注册、查询、别名解析。
"""

from __future__ import annotations

import threading

from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor
from app.model_registry.models import _normalize_lookup_key


class ModelRegistryRepository:
    """
    线程安全的模型注册表。
    """

    def __init__(self) -> None:
        self._by_name: dict[str, ModelInfo] = {}
        self._alias_index: dict[str, str] = {}
        self._by_model_id: dict[str, str] = {}
        self._lock = threading.RLock()

    def register(
        self,
        model: ModelInfo,
        *,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if model.name in self._by_name and not overwrite:
                raise ValueError(
                    f"Model '{model.name}' already registered"
                )

            self._by_name[model.name] = model
            self._by_model_id[model.model_id] = model.name
            self._alias_index[_normalize_lookup_key(model.name)] = (
                model.name
            )
            self._alias_index[_normalize_lookup_key(model.model_id)] = (
                model.name
            )

            for alias in model.normalized_aliases():
                if (
                    alias in self._alias_index
                    and self._alias_index[alias] != model.name
                    and not overwrite
                ):
                    existing = self._alias_index[alias]
                    raise ValueError(
                        f"Alias '{alias}' already maps to '{existing}'"
                    )
                self._alias_index[alias] = model.name

    def unregister(self, name: str) -> None:
        with self._lock:
            model = self._by_name.pop(name, None)
            if model is None:
                return

            self._by_model_id.pop(model.model_id, None)
            keys_to_drop = [
                _normalize_lookup_key(model.name),
                _normalize_lookup_key(model.model_id),
                *model.normalized_aliases(),
            ]
            for key in keys_to_drop:
                if self._alias_index.get(key) == name:
                    self._alias_index.pop(key, None)

    def get(self, name: str) -> ModelInfo:
        with self._lock:
            model = self._by_name.get(name)
            if model is not None:
                return model
            raise KeyError(f"Unknown model: {name}")

    def try_get(self, name: str) -> ModelInfo | None:
        with self._lock:
            return self._by_name.get(name)

    def resolve(self, name_or_alias: str) -> ModelInfo:
        """
        按注册名、model_id 或别名解析。
        """

        raw = (name_or_alias or "").strip()
        if not raw:
            raise KeyError("Empty model name")

        with self._lock:
            if raw in self._by_name:
                return self._by_name[raw]

            key = _normalize_lookup_key(raw)
            resolved_name = self._alias_index.get(key)
            if resolved_name:
                return self._by_name[resolved_name]

            if "/" in raw:
                by_id = self._by_model_id.get(raw)
                if by_id:
                    return self._by_name[by_id]

        raise KeyError(f"Unknown model or alias: {name_or_alias}")

    def list_models(
        self,
        *,
        provider: ModelVendor | None = None,
        capability: str | None = None,
    ) -> list[ModelInfo]:
        with self._lock:
            items = list(self._by_name.values())

        if provider is not None:
            items = [m for m in items if m.provider == provider]

        if capability:
            cap = capability.strip().lower()
            items = [
                m
                for m in items
                if cap in {c.lower() for c in m.capabilities}
            ]

        return sorted(items, key=lambda m: (m.provider.value, m.name))

    def all_names(self) -> list[str]:
        with self._lock:
            return sorted(self._by_name.keys())
