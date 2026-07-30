"""
Inference Gateway 类型与 Token 统计结构。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class InferenceBackendKind(str, Enum):
    OPENAI = "openai"
    VLLM = "vllm"
    SGLANG = "sglang"
    TGI = "tgi"
    LOCAL = "local"


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_openai_usage(cls, usage: Any | None) -> TokenUsage:
        if usage is None:
            return cls()
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total = int(getattr(usage, "total_tokens", 0) or 0)
        if total <= 0:
            total = prompt + completion
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    @classmethod
    def estimate_from_text(
        cls,
        prompt_text: str,
        completion_text: str,
    ) -> TokenUsage:
        prompt = max(1, len(prompt_text) // 4)
        completion = max(0, len(completion_text) // 4)
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
        )


class GatewayCallMeta(BaseModel):
    request_id: str
    backend: InferenceBackendKind
    model: str
    duration_ms: float = 0.0
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cache_hit: bool = False
    cache_layer: str | None = None


class GatewayChatResult(BaseModel):
    """网关一次 chat 的完整结果。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: Any
    meta: GatewayCallMeta


class TokenStatsSnapshot(BaseModel):
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    by_backend: dict[str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)
