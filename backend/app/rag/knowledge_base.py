from app.rag.chunker.base import Chunker
from app.rag.chunker.paragraph import ParagraphChunker
from app.rag.embedding.base import EmbeddingProvider
from app.rag.retriever import Retriever
from app.rag.types import Document
from app.rag.types import ScoredDocument
from app.rag.vectorstore.base import VectorStore


class KnowledgeBase:
    """
    知识库管理。

    负责：导入文档 → 切分 → 建立索引 → 提供 search。
    后续可扩展 Multi KB、GraphRAG 等能力。
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        chunker: Chunker | None = None,
        retriever: Retriever | None = None,
        kb_id: str = "default",
    ):

        self.kb_id = kb_id

        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

        self._chunker = (
            chunker or ParagraphChunker()
        )

        self._retriever = (
            retriever
            or Retriever(
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
        )

    def ingest(
        self,
        document: Document,
    ) -> list[Document]:
        """
        导入文档：切分 → embedding → 写入 VectorStore。
        """

        chunks = self._chunker.chunk(document)

        for chunk in chunks:

            chunk.metadata.setdefault(
                "kb_id",
                self.kb_id,
            )

        if not chunks:

            return chunks

        vectors = self._embedding_provider.embed(
            [chunk.content for chunk in chunks]
        )

        for chunk, vector in zip(
            chunks,
            vectors,
            strict=True,
        ):

            self._vector_store.add(
                chunk,
                vector,
            )

        return chunks

    def delete(
        self,
        document_id: str,
    ) -> None:

        self._vector_store.delete(
            document_id
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.0,
    ) -> list[ScoredDocument]:
        """
        检索知识库。
        """

        return self._retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )

    @property
    def retriever(self) -> Retriever:

        return self._retriever
