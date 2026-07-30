"""
从 YAML 动态加载 Model Registry。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.model_registry.models import ModelInfo
from app.model_registry.repository import ModelRegistryRepository

DEFAULT_MODELS_FILE = (
    Path(__file__).resolve().parent / "data" / "models.yaml"
)


def load_models_from_yaml(
    path: Path | str,
) -> list[ModelInfo]:
    """
    解析 YAML 文件，返回 ModelInfo 列表（不写仓库）。
    """

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Model registry file not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    payload: dict[str, Any] = yaml.safe_load(raw_text) or {}

    entries = payload.get("models")
    if not isinstance(entries, list):
        raise ValueError(
            f"Invalid registry YAML: 'models' must be a list in {file_path}"
        )

    models: list[ModelInfo] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid model entry at index {index} in {file_path}"
            )
        models.append(ModelInfo.model_validate(item))

    return models


def load_into_repository(
    repository: ModelRegistryRepository,
    path: Path | str,
    *,
    overwrite: bool = True,
) -> int:
    """
    将 YAML 中的模型写入仓库，返回加载条数。
    """

    models = load_models_from_yaml(path)
    for model in models:
        repository.register(model, overwrite=overwrite)
    return len(models)
