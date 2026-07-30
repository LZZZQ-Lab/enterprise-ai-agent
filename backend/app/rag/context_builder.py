from __future__ import annotations

from app.llm.types import Message
from app.rag.types import ScoredDocument


class RAGContextBuilder:
    """
    将检索结果组装为 LLM Prompt Context。

    流程：Relevant Documents → system 知识块 + user 问题。
    """

    def __init__(
        self,
        *,
        instruction: str | None = None,
    ) -> None:

        self._instruction = instruction or (
            "请根据以下检索到的企业知识回答用户问题。"
            "答案应准确、简洁；若知识不足以回答，请明确说明。"
            "不要编造未出现在知识中的事实。"
        )

    def build_messages(
        self,
        question: str,
        retrieved: list[ScoredDocument],
    ) -> list[Message]:
        """
        构建送入 LLM 的 messages。
        """

        knowledge_block = self._format_knowledge(
            retrieved
        )

        system_content = self._instruction

        if knowledge_block:

            system_content = (
                f"{self._instruction}\n\n"
                f"--- 检索知识 ---\n"
                f"{knowledge_block}"
            )

        return [
            Message(
                role="system",
                content=system_content,
            ),
            Message(
                role="user",
                content=question,
            ),
        ]

    def build_context_text(
        self,
        retrieved: list[ScoredDocument],
    ) -> str:
        """
        仅生成注入 Prompt 的知识文本（便于测试与日志）。
        """

        return self._format_knowledge(retrieved)

    @staticmethod
    def _format_knowledge(
        retrieved: list[ScoredDocument],
    ) -> str:

        if not retrieved:

            return ""

        sections: list[str] = []

        for index, scored in enumerate(
            retrieved,
            start=1,
        ):

            metadata = scored.document.metadata

            source = (
                metadata.get("source_path")
                or metadata.get("file_name")
                or metadata.get("source")
                or scored.document.id
            )

            sections.append(
                f"[{index}] "
                f"(score={scored.score:.4f}, source={source})\n"
                f"{scored.document.content}"
            )

        return "\n\n".join(sections)
