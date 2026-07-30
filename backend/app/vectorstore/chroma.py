from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.rag.types import Document
from app.rag.types import ScoredDocument
from app.vectorstore.base import BaseVectorStore


class ChromaVectorStore(BaseVectorStore):
    """
    基于 Chroma 的持久化向量存储。

    Embedding 由上层 RAG Pipeline 计算后传入，本类不负责调用 Embedding 模型。
    """

    def __init__(
        self,
        *,
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
        dimension: int | None = None,
    ) -> None:

        app_settings = get_settings()

        self._persist_directory = Path(
            persist_directory
            or app_settings.CHROMA_PERSIST_DIR
        ).expanduser()

        self._collection_name = (
            collection_name
            or app_settings.CHROMA_COLLECTION
        )

        self._dimension = (
            dimension
            if dimension is not None
            else (
                app_settings.EMBEDDING_DIMENSION
                if app_settings.EMBEDDING_DIMENSION > 0
                else None
            )
        )

        self._persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        client = self._create_client(self._persist_directory)

        self._collection = client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        document: Document,
        vector: list[float],
    ) -> None:

        self._validate_vector(vector)

        if self._dimension is None:

            self._dimension = len(vector)

        self._collection.upsert(
            ids=[document.id],
            embeddings=[vector],
            documents=[document.content],
            metadatas=[
                self._sanitize_metadata(
                    document.metadata
                )
            ],
        )

    def delete(
        self,
        document_id: str,
    ) -> None:

        self._collection.delete(
            ids=[document_id]
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[ScoredDocument]:

        self._validate_vector(query_vector)

        if top_k <= 0:

            return []

        raw = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return self._parse_query_results(raw)

    @staticmethod
    def _create_client(
        persist_directory: Path,
    ):
        """
        延迟导入 chromadb，避免未安装时影响其它模块加载。

        若配置了 ``CHROMA_HOST``，使用 Chroma Server（Docker 生产部署）。
        """

        try:

            import chromadb

        except ImportError as error:

            raise RuntimeError(
                "Chroma vector store requires chromadb. "
                "Install with: pip install chromadb"
            ) from error

        settings = get_settings()

        if settings.CHROMA_HOST.strip():

            return chromadb.HttpClient(
                host=settings.CHROMA_HOST.strip(),
                port=settings.CHROMA_PORT,
            )

        return chromadb.PersistentClient(
            path=str(persist_directory)
        )

    def _parse_query_results(
        self,
        raw: dict[str, Any],
    ) -> list[ScoredDocument]:

        ids = (raw.get("ids") or [[]])[0]
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        scored: list[ScoredDocument] = []

        for doc_id, content, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=False,
        ):

            if not doc_id:

                continue

            score = self._distance_to_score(
                float(distance)
            )

            scored.append(
                ScoredDocument(
                    document=Document(
                        id=str(doc_id),
                        content=content or "",
                        metadata=dict(metadata or {}),
                    ),
                    score=score,
                )
            )

        scored.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return scored

    @staticmethod
    def _distance_to_score(
        distance: float,
    ) -> float:
        """
        Chroma cosine 距离 → 相似度分数（越大越相似）。
        """

        return max(0.0, 1.0 - distance)

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
    def _sanitize_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, str | int | float | bool]:
        """
        Chroma 仅接受标量 metadata。
        """

        sanitized: dict[str, str | int | float | bool] = {}

        for key, value in metadata.items():

            if isinstance(
                value,
                (str, int, float, bool),
            ):

                sanitized[key] = value

            elif value is None:

                continue

            else:

                sanitized[key] = str(value)

        return sanitized
