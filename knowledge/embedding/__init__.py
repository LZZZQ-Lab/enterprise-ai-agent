"""
Embedding Provider（Task 9.1 canonical import）。

Implementation: ``backend/app/embedding/`` · ``backend/app/rag/embedding/``
"""

from app.embedding import *  # noqa: F403
from app.rag.embedding.base import EmbeddingProvider
from app.rag.embedding.fake import FakeEmbeddingProvider

from app.embedding import __all__ as _embedding_all

__all__ = list(dict.fromkeys([*_embedding_all, "EmbeddingProvider", "FakeEmbeddingProvider"]))
