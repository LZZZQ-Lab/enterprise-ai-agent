from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.rag.vectorstore.inmemory import InMemoryVectorStore
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.chroma import ChromaVectorStore

SUPPORTED_VECTOR_STORES = frozenset({"memory", "chroma"})


def create_vector_store(
    provider_name: str | None = None,
    *,
    collection_name: str | None = None,
    persist_directory: str | None = None,
    dimension: int | None = None,
) -> BaseVectorStore:
    """
    根据配置创建向量库实例。

    RAG Pipeline / KnowledgeBase 装配层调用；Agent 禁止直接使用。
    """

    app_settings = get_settings()

    name = (
        provider_name or app_settings.VECTOR_STORE_PROVIDER
    ).lower().strip()

    resolved_dimension = dimension

    if resolved_dimension is None and app_settings.EMBEDDING_DIMENSION > 0:

        resolved_dimension = app_settings.EMBEDDING_DIMENSION

    if name == "memory":

        return InMemoryVectorStore(
            dimension=resolved_dimension,
        )

    if name == "chroma":

        return ChromaVectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
            dimension=resolved_dimension,
        )

    raise ValueError(
        f"Unknown vector store '{name}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_VECTOR_STORES))}"
    )


@lru_cache
def get_vector_store() -> BaseVectorStore:

    return create_vector_store()


def reset_vector_store_cache() -> None:

    get_vector_store.cache_clear()
