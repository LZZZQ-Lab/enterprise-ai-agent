"""
向后兼容：RAG 层 VectorStore 即 app.vectorstore.BaseVectorStore。
"""

from app.vectorstore.base import BaseVectorStore

VectorStore = BaseVectorStore

__all__ = ["VectorStore", "BaseVectorStore"]
