from app.embedding.base import BaseEmbedding
from app.embedding.fake import FakeEmbedding

FakeEmbeddingProvider = FakeEmbedding

__all__ = ["FakeEmbeddingProvider", "FakeEmbedding"]
