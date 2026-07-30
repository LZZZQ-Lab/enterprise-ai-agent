import math

from app.rag.types import Document
from app.rag.types import ScoredDocument
from app.vectorstore.base import BaseVectorStore as VectorStore


class InMemoryVectorStore(VectorStore):
    """
    基于内存的向量存储实现。

    使用余弦相似度进行检索，适合开发测试。
    """

    def __init__(
        self,
        dimension: int | None = None,
    ):

        self._dimension = dimension

        self._entries: dict[
            str,
            tuple[list[float], Document]
        ] = {}

    def add(
        self,
        document: Document,
        vector: list[float],
    ) -> None:

        self._validate_vector(vector)

        if self._dimension is None:

            self._dimension = len(vector)

        self._entries[document.id] = (
            vector,
            document,
        )

    def delete(
        self,
        document_id: str,
    ) -> None:

        self._entries.pop(
            document_id,
            None,
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[ScoredDocument]:

        self._validate_vector(query_vector)

        if not self._entries:

            return []

        scored = [
            ScoredDocument(
                document=document,
                score=self._cosine_similarity(
                    query_vector,
                    vector,
                ),
            )
            for vector, document in self._entries.values()
        ]

        scored.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return scored[:top_k]

    def _validate_vector(
        self,
        vector: list[float],
    ) -> None:

        if not vector:

            raise ValueError(
                "Vector must not be empty."
            )

        if self._dimension is None:

            return

        if len(vector) != self._dimension:

            raise ValueError(
                "Vector dimension mismatch: "
                f"expected {self._dimension}, "
                f"got {len(vector)}."
            )

    @staticmethod
    def _cosine_similarity(
        left: list[float],
        right: list[float],
    ) -> float:

        dot_product = sum(
            left_value * right_value
            for left_value, right_value in zip(
                left,
                right,
                strict=True,
            )
        )

        left_norm = math.sqrt(
            sum(value * value for value in left)
        )

        right_norm = math.sqrt(
            sum(value * value for value in right)
        )

        if left_norm == 0 or right_norm == 0:

            return 0.0

        return dot_product / (left_norm * right_norm)
