from __future__ import annotations

import hashlib
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.rag.types import Document as RagDocument


@dataclass
class Document:
    """
    企业知识库统一文档结构。

    对外仅暴露 content 与 metadata；document_id 等索引字段放在 metadata 中。
    """

    content: str

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        """
        文档唯一标识，优先 metadata.document_id，否则按 content 哈希。
        """

        explicit = self.metadata.get("document_id")

        if explicit:

            return str(explicit)

        digest = hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()[:16]

        return f"doc-{digest}"

    def to_rag_document(self) -> RagDocument:
        """
        转为 RAG 层 Document，供 KnowledgeBase.ingest 使用。
        """

        return RagDocument(
            id=self.document_id,
            content=self.content,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        序列化为 { content, metadata } 形态。
        """

        return {
            "content": self.content,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> Document:

        return cls(
            content=str(data.get("content", "")),
            metadata=dict(data.get("metadata") or {}),
        )
