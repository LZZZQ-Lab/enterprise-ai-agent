from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.embedding.base import BaseEmbedding
from app.embedding.factory import get_embedding_provider
from app.knowledge.loader import DocumentLoader
from app.knowledge.splitter import DocumentSplitter
from app.llm.base import BaseLLM
from app.llm.factory import get_llm_client
from app.rag.context_builder import RAGContextBuilder
from app.rag.knowledge_base import KnowledgeBase
from app.rag.retriever import Retriever
from app.rag.types import RAGAnswer
from app.rag.types import SourceDocument
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.manager import get_vector_store


class RAGPipeline:
    """
    企业 RAG 流水线：入库 → 检索 → Prompt → LLM → 答案与来源。

    业务与 Agent 通过本类（或模块级 ask）访问知识问答，不直连向量库。
    """

    def __init__(
        self,
        *,
        knowledge_base: KnowledgeBase | None = None,
        retriever: Retriever | None = None,
        llm: BaseLLM | None = None,
        context_builder: RAGContextBuilder | None = None,
        embedding_provider: BaseEmbedding | None = None,
        vector_store: BaseVectorStore | None = None,
        top_k: int = 3,
        score_threshold: float = 0.0,
        kb_id: str = "default",
    ) -> None:

        embedding = (
            embedding_provider or get_embedding_provider()
        )

        store = vector_store or get_vector_store()

        self._kb = knowledge_base or KnowledgeBase(
            embedding_provider=embedding,
            vector_store=store,
            kb_id=kb_id,
        )

        self._retriever = retriever or self._kb.retriever

        self._llm = llm or get_llm_client()

        self._context_builder = (
            context_builder or RAGContextBuilder()
        )

        self._loader = DocumentLoader()
        self._splitter = DocumentSplitter()

        self._top_k = top_k
        self._score_threshold = score_threshold

    def ingest_file(
        self,
        path: str | Path,
        *,
        extra_metadata: dict | None = None,
    ) -> int:
        """
        上传/导入单个企业文档：Loader → Chunk → Embedding → Vector DB。

        返回写入的 chunk 数量。
        """

        document = self._loader.load(
            path,
            extra_metadata=extra_metadata,
        )

        return self.ingest_document(document)

    def ingest_directory(
        self,
        directory: str | Path,
        *,
        recursive: bool = False,
    ) -> int:
        """
        批量导入目录下支持的文档。
        """

        documents = self._loader.load_directory(
            directory,
            recursive=recursive,
        )

        total = 0

        for document in documents:

            total += self.ingest_document(document)

        return total

    def ingest_document(
        self,
        document,
    ) -> int:
        """
        导入 app.knowledge.document.Document。
        """

        chunks = self._splitter.split(document)

        for chunk in chunks:

            self._kb.ingest(
                chunk.to_rag_document()
            )

        return len(chunks)

    def retrieve(
        self,
        question: str,
        *,
        top_k: int | None = None,
    ) -> list[SourceDocument]:
        """
        仅检索，不调用 LLM。
        """

        limit = top_k if top_k is not None else self._top_k

        scored = self._retriever.retrieve(
            query=question,
            top_k=limit,
            score_threshold=self._score_threshold,
        )

        return [
            SourceDocument.from_scored(item)
            for item in scored
        ]

    def ask(
        self,
        question: str,
    ) -> RAGAnswer:
        """
        知识库问答：Question → Embedding → Search → Context → LLM。
        """

        scored = self._retriever.retrieve(
            query=question,
            top_k=self._top_k,
            score_threshold=self._score_threshold,
        )

        sources = [
            SourceDocument.from_scored(item)
            for item in scored
        ]

        messages = self._context_builder.build_messages(
            question,
            scored,
        )

        result = self._llm.chat(
            messages,
            use_tools=False,
        )

        answer = (result.content or "").strip()

        return RAGAnswer(
            question=question,
            answer=answer,
            sources=sources,
        )

    @property
    def knowledge_base(self) -> KnowledgeBase:

        return self._kb


def create_rag_pipeline(
    **kwargs,
) -> RAGPipeline:

    from app.config.settings import get_settings

    settings = get_settings()

    kwargs.setdefault("top_k", settings.RAG_TOP_K)
    kwargs.setdefault(
        "score_threshold",
        settings.RAG_SCORE_THRESHOLD,
    )

    return RAGPipeline(**kwargs)


@lru_cache
def get_rag_pipeline() -> RAGPipeline:

    return create_rag_pipeline()


def reset_rag_pipeline_cache() -> None:

    get_rag_pipeline.cache_clear()


def ask(
    question: str,
) -> RAGAnswer:
    """
    模块级知识库问答入口：rag.ask(question)。
    """

    return get_rag_pipeline().ask(question)
