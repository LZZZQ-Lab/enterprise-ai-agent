from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class Document:
    """
    RAG 知识库中的文档单元。

    表示一段可被索引、检索的文本内容。
    后续 Chunker 会将 Document 切分为更小的片段再写入 VectorStore。
    """

    id: str

    content: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ScoredDocument:
    """
    带相似度分数的检索结果。
    """

    document: Document

    score: float


@dataclass
class SourceDocument:
    """
    RAG 问答返回的引用来源。
    """

    document_id: str

    content: str

    score: float

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_scored(
        cls,
        scored: ScoredDocument,
    ) -> SourceDocument:

        return cls(
            document_id=scored.document.id,
            content=scored.document.content,
            score=scored.score,
            metadata=dict(scored.document.metadata),
        )


@dataclass
class RAGAnswer:
    """
    RAG Pipeline 问答结果：答案 + 来源文档。
    """

    question: str

    answer: str

    sources: list[SourceDocument] = field(
        default_factory=list
    )

