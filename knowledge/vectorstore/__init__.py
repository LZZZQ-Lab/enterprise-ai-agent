"""
Vector Store（Task 9.1 canonical import）。

Implementation: ``backend/app/vectorstore/`` · ``backend/app/rag/vectorstore/``
"""

from app.rag.vectorstore.base import VectorStore
from app.rag.vectorstore.inmemory import InMemoryVectorStore
from app.vectorstore import *  # noqa: F403

from app.vectorstore import __all__ as _vs_all

__all__ = list(dict.fromkeys([*_vs_all, "VectorStore", "InMemoryVectorStore"]))
