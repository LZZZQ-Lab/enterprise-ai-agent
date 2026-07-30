from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.document import Document
from app.rag.types import Document as RagDocument


@dataclass
class DocumentSplitter:
    """
    将整篇 Document 切分为可索引片段。

    默认按段落（空行）切分；单段过长时按 max_chunk_chars 再切。
    """

    max_chunk_chars: int = 2000

    def split(
        self,
        document: Document,
    ) -> list[Document]:
        """
        切分文档，返回带 chunk_index / parent_id 的 Document 列表。
        """

        parent_id = document.document_id

        segments = self._segment_text(document.content)

        if not segments:

            return [document]

        chunks: list[Document] = []

        for index, segment in enumerate(segments):

            chunk_metadata = {
                **document.metadata,
                "chunk_index": index,
                "parent_id": parent_id,
                "splitter": "paragraph",
            }

            chunk_metadata["document_id"] = (
                f"{parent_id}#{index}"
            )

            chunks.append(
                Document(
                    content=segment,
                    metadata=chunk_metadata,
                )
            )

        return chunks

    def split_to_rag_documents(
        self,
        document: Document,
    ) -> list[RagDocument]:
        """
        切分并直接转为 RAG Document 列表。
        """

        return [
            chunk.to_rag_document()
            for chunk in self.split(document)
        ]

    def _segment_text(
        self,
        text: str,
    ) -> list[str]:

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        if len(paragraphs) <= 1:

            paragraphs = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

        segments: list[str] = []

        for paragraph in paragraphs:

            segments.extend(
                self._split_long_paragraph(paragraph)
            )

        return segments

    def _split_long_paragraph(
        self,
        paragraph: str,
    ) -> list[str]:

        if len(paragraph) <= self.max_chunk_chars:

            return [paragraph]

        parts: list[str] = []

        start = 0

        while start < len(paragraph):

            end = min(
                start + self.max_chunk_chars,
                len(paragraph),
            )

            if end < len(paragraph):

                window = paragraph[start:end]
                break_at = max(
                    window.rfind("\n"),
                    window.rfind("。"),
                    window.rfind(". "),
                )

                if break_at > self.max_chunk_chars // 4:

                    end = start + break_at + 1

            piece = paragraph[start:end].strip()

            if piece:

                parts.append(piece)

            start = end

        return parts or [paragraph[: self.max_chunk_chars]]
