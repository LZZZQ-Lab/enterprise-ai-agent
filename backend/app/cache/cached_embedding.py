"""
带 Embedding Cache 的 Provider 包装。
"""

from __future__ import annotations

from app.cache.manager import cache_enabled
from app.cache.manager import get_model_cache_manager
from app.embedding.base import BaseEmbedding


class CachedEmbeddingProvider(BaseEmbedding):
    def __init__(self, inner: BaseEmbedding) -> None:
        self._inner = inner
        self._cache = get_model_cache_manager().embedding_for(
            model=_resolve_embedding_model(inner),
            dimension=inner.dimension,
        )

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not cache_enabled() or not texts:
            return self._inner.embed(texts)

        cached = self._cache.get_many(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for index, (text, vector) in enumerate(zip(texts, cached, strict=True)):
            if vector is None:
                missing_indices.append(index)
                missing_texts.append(text)

        if not missing_texts:
            return [vector for vector in cached if vector is not None]

        computed = self._inner.embed(missing_texts)
        self._cache.set_many(missing_texts, computed)

        output: list[list[float]] = []
        computed_iter = iter(computed)
        for vector in cached:
            if vector is not None:
                output.append(vector)
            else:
                output.append(next(computed_iter))
        return output


def _resolve_embedding_model(inner: BaseEmbedding) -> str:
    for attr in ("_model", "model_id", "model"):
        value = getattr(inner, attr, None)
        if value:
            return str(value)
    return type(inner).__name__.lower()
