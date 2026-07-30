"""
向后兼容：RAG 层统一使用 app.embedding.BaseEmbedding。

新代码请 from app.embedding import BaseEmbedding。
"""

from app.embedding.base import BaseEmbedding

EmbeddingProvider = BaseEmbedding

__all__ = ["EmbeddingProvider", "BaseEmbedding"]
