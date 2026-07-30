from app.rag.compression.base import ContextCompressor
from app.rag.compression.none import NoCompression
from app.rag.embedding.base import EmbeddingProvider
from app.rag.strategy.base import RetrieverStrategy
from app.rag.strategy.similarity import SimilaritySearchStrategy
from app.rag.types import ScoredDocument
from app.rag.vectorstore.base import VectorStore


class Retriever:
    """
    RAG 检索器。

    负责：query → embedding → vector search → Document
    不直接操作 Prompt，与 ChatAgent 解耦。
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        strategy: RetrieverStrategy | None = None,
        compressor: ContextCompressor | None = None,
    ):

        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

        self._strategy = (
            strategy
            or SimilaritySearchStrategy(
                vector_store=vector_store,
            )
        )

        self._compressor = (
            compressor or NoCompression()
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.0,
    ) -> list[ScoredDocument]:
        """
        检索与 query 最相关的文档。
        """

        query_vector = self._embedding_provider.embed_one(
            query
        )

        results = self._strategy.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        return self._compressor.compress(
            results
        )
