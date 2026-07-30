from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.rag.types import Document
from app.rag.types import ScoredDocument


class BaseVectorStore(ABC):
    """
    向量存储统一抽象。

    Agent 与业务代码只依赖本接口；禁止直接调用 Chroma 等后端 SDK。
    """

    @abstractmethod
    def add(
        self,
        document: Document,
        vector: list[float],
    ) -> None:
        """
        写入或更新一条文档向量（通常对应一个 Document Chunk）。
        """

        pass

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[ScoredDocument]:
        """
        向量相似度检索，分数越高表示越相关。
        """

        pass

    def delete(
        self,
        document_id: str,
    ) -> None:
        """
        按文档 ID 删除；子类可覆盖。
        """

        raise NotImplementedError(
            f"{type(self).__name__} does not support delete."
        )
