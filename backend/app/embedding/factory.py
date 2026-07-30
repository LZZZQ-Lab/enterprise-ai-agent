from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.embedding.base import BaseEmbedding
from app.embedding.fake import FakeEmbedding
from app.embedding.local_embedding import LocalEmbedding
from app.embedding.openai_embedding import OpenAIEmbedding

SUPPORTED_EMBEDDING_PROVIDERS = frozenset(
    {"openai", "local", "fake"}
)


def create_embedding_provider(
    provider_name: str | None = None,
) -> BaseEmbedding:
    """
    根据配置创建 Embedding Provider。

    业务与 RAG 应通过 get_embedding_provider() 获取实例，禁止直接 new 具体类。
    """

    app_settings = get_settings()

    name = (
        provider_name or app_settings.EMBEDDING_PROVIDER
    ).lower().strip()

    if name == "openai":
        inner: BaseEmbedding = OpenAIEmbedding()
    elif name == "local":
        inner = LocalEmbedding()
    elif name == "fake":
        dimension = (
            app_settings.EMBEDDING_DIMENSION
            if app_settings.EMBEDDING_DIMENSION > 0
            else 128
        )
        inner = FakeEmbedding(dimension=dimension)
    else:
        raise ValueError(
            f"Unknown embedding provider '{name}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EMBEDDING_PROVIDERS))}"
        )

    if app_settings.ENABLE_MODEL_CACHE:
        from app.cache.cached_embedding import CachedEmbeddingProvider

        return CachedEmbeddingProvider(inner)

    return inner


@lru_cache
def get_embedding_provider() -> BaseEmbedding:

    return create_embedding_provider()


def reset_embedding_provider_cache() -> None:

    get_embedding_provider.cache_clear()
