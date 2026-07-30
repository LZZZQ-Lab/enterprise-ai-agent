"""Embedding Provider 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.embedding.base import BaseEmbedding
from app.embedding.fake import FakeEmbedding
from app.embedding.factory import create_embedding_provider
from app.embedding.factory import reset_embedding_provider_cache
from app.embedding.local_embedding import LocalEmbedding
from app.embedding.openai_embedding import OpenAIEmbedding
from app.rag.knowledge_base import KnowledgeBase
from app.rag.types import Document
from app.rag.vectorstore.inmemory import InMemoryVectorStore


@pytest.fixture(autouse=True)
def _disable_embedding_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """避免 CachedEmbeddingProvider 包装导致 isinstance 失败。"""

    monkeypatch.setenv("ENABLE_MODEL_CACHE", "false")

    from app.config.settings import reset_settings_cache

    reset_settings_cache()
    reset_embedding_provider_cache()
    yield
    reset_embedding_provider_cache()
    reset_settings_cache()


def test_base_embedding_is_abstract() -> None:

    with pytest.raises(TypeError):

        BaseEmbedding()


def test_fake_embed_batch_and_dimension() -> None:

    provider = FakeEmbedding(dimension=64)

    assert provider.dimension == 64

    vectors = provider.embed(["hello", "world", ""])

    assert len(vectors) == 3
    assert len(vectors[0]) == 64
    assert vectors[0] == provider.embed_one("hello")
    assert vectors[2] == [0.0] * 64


def test_create_fake_provider() -> None:

    provider = create_embedding_provider("fake")

    assert isinstance(provider, FakeEmbedding)


def test_create_openai_provider() -> None:

    provider = create_embedding_provider("openai")

    assert isinstance(provider, OpenAIEmbedding)


def test_create_local_provider_type() -> None:

    pytest.importorskip("sentence_transformers")

    provider = create_embedding_provider("local")

    assert isinstance(provider, LocalEmbedding)


def test_openai_embed_calls_api() -> None:

    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(index=0, embedding=[0.1, 0.2]),
        MagicMock(index=1, embedding=[0.3, 0.4]),
    ]

    with patch("app.embedding.openai_embedding.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAIEmbedding(
            api_key="test-key",
            base_url="http://test/v1",
            model="text-embedding-3-small",
            dimension=2,
        )

        vectors = provider.embed(["a", "b"])

    mock_client.embeddings.create.assert_called_once_with(
        input=["a", "b"],
        model="text-embedding-3-small",
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_knowledge_base_uses_embedding_abstraction_only() -> None:

    embedding = FakeEmbedding(dimension=32)
    store = InMemoryVectorStore(dimension=32)
    kb = KnowledgeBase(
        embedding_provider=embedding,
        vector_store=store,
    )

    doc = Document(
        id="d1",
        content="第一段。\n\n第二段关于企业知识库。",
        metadata={},
    )

    chunks = kb.ingest(doc)

    assert len(chunks) >= 1

    hits = kb.search(
        query="企业知识库",
        top_k=1,
    )

    assert hits
    assert hits[0].score >= 0


def test_factory_unknown_provider() -> None:

    with pytest.raises(ValueError, match="Unknown embedding provider"):

        create_embedding_provider("unknown")


def test_embedding_provider_from_env_fake(monkeypatch) -> None:

    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")

    from app.config.settings import reset_settings_cache

    reset_settings_cache()
    reset_embedding_provider_cache()

    from app.embedding.factory import get_embedding_provider

    provider = get_embedding_provider()

    assert isinstance(provider, FakeEmbedding)

    reset_embedding_provider_cache()
