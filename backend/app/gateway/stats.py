"""
统一 Token 累计统计。
"""

from __future__ import annotations

import threading

from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenStatsSnapshot
from app.gateway.types import TokenUsage

_lock = threading.Lock()
_stats = TokenStatsSnapshot()


def record_token_usage(
    *,
    backend: InferenceBackendKind,
    model: str,
    usage: TokenUsage,
) -> None:
    global _stats

    with _lock:
        _stats.total_requests += 1
        _stats.prompt_tokens += usage.prompt_tokens
        _stats.completion_tokens += usage.completion_tokens
        _stats.total_tokens += usage.total_tokens

        backend_key = backend.value
        model_key = model or "unknown"

        _stats.by_backend[backend_key] = (
            _stats.by_backend.get(backend_key, 0) + usage.total_tokens
        )
        _stats.by_model[model_key] = (
            _stats.by_model.get(model_key, 0) + usage.total_tokens
        )


def get_token_stats() -> TokenStatsSnapshot:
    with _lock:
        return _stats.model_copy(deep=True)


def reset_token_stats() -> None:
    global _stats

    with _lock:
        _stats = TokenStatsSnapshot()
