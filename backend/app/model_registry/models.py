"""
Model Registry 数据模型（Task 7.1）。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class ModelVendor(str, Enum):
    """模型厂商 / 系列。"""

    OPENAI = "openai"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    LLAMA = "llama"


class ModelCost(BaseModel):
    """
    推理成本（每百万 token，便于路由与计费展示）。
    """

    input_per_1m: float = 0.0
    output_per_1m: float = 0.0
    currency: str = "USD"


class ModelInfo(BaseModel):
    """
    注册表中的模型元数据。

    ``name`` 为注册表主键；``model_id`` 为调用推理 API 时使用的模型标识。
    """

    name: str
    model_id: str
    provider: ModelVendor
    context_length: int = Field(..., ge=1)
    max_tokens: int = Field(..., ge=1)
    cost: ModelCost = Field(default_factory=ModelCost)
    capabilities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "model_id")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("aliases", mode="before")
    @classmethod
    def _normalize_aliases(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        return [
            item.strip()
            for item in value
            if item and str(item).strip()
        ]

    def normalized_aliases(self) -> list[str]:
        """用于索引的小写别名（不含主键）。"""

        keys: set[str] = set()
        for raw in self.aliases:
            keys.add(_normalize_lookup_key(raw))
        return sorted(keys)


def _normalize_lookup_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "-")
