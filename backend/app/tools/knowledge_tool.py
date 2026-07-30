from __future__ import annotations

import json
from typing import Any

from app.rag.pipeline import RAGPipeline
from app.rag.pipeline import create_rag_pipeline
from app.rag.types import SourceDocument
from app.tools.base_tool import BaseTool
from app.tools.types import ToolContext
from app.tools.types import ToolResult

_REGISTERED = False


class SearchKnowledgeTool(BaseTool):
    """
    企业知识库检索 Tool。

    Agent Loop 通过 Tool Calling 调用 search_knowledge，由 LLM 判断是否需要检索。
    """

    def __init__(
        self,
        pipeline: RAGPipeline | None = None,
        *,
        default_top_k: int = 3,
    ) -> None:

        self._pipeline = pipeline
        self._default_top_k = default_top_k

    @property
    def name(self) -> str:

        return "search_knowledge"

    @property
    def description(self) -> str:

        return (
            "Search the enterprise knowledge base for internal "
            "documents, policies, product information, and "
            "company-specific facts. Use this tool when the "
            "user question requires information that may exist "
            "in uploaded company documents—not for general world "
            "knowledge or small talk."
        )

    @property
    def schema(self) -> dict[str, Any]:

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Search query describing what "
                                "to look up in the knowledge base"
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": (
                                "Maximum number of passages "
                                "to return (default 3)"
                            ),
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def _get_pipeline(self) -> RAGPipeline:

        if self._pipeline is not None:

            return self._pipeline

        return create_rag_pipeline()

    def execute(
        self,
        context: ToolContext,
    ) -> ToolResult:

        arguments = context.arguments or {}

        query = str(
            arguments.get("query", "")
        ).strip()

        if not query:

            return ToolResult(
                success=False,
                content="Parameter 'query' is required.",
            )

        top_k_raw = arguments.get("top_k")

        top_k = self._default_top_k

        if top_k_raw is not None:

            try:

                top_k = max(1, int(top_k_raw))

            except (TypeError, ValueError):

                top_k = self._default_top_k

        try:

            sources = self._get_pipeline().retrieve(
                query,
                top_k=top_k,
            )

        except Exception as error:

            return ToolResult(
                success=False,
                content=f"Knowledge search failed: {error}",
            )

        if not sources:

            return ToolResult(
                success=True,
                content=(
                    "No relevant documents found in the "
                    "enterprise knowledge base."
                ),
            )

        payload = {
            "query": query,
            "result_count": len(sources),
            "passages": [
                self._source_to_dict(source)
                for source in sources
            ],
        }

        return ToolResult(
            success=True,
            content=json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
        )

    @staticmethod
    def _source_to_dict(
        source: SourceDocument,
    ) -> dict[str, Any]:

        return {
            "document_id": source.document_id,
            "score": source.score,
            "source": (
                source.metadata.get("source_path")
                or source.metadata.get("file_name")
                or source.document_id
            ),
            "content": source.content,
            "metadata": source.metadata,
        }


def register_search_knowledge_tool(
    pipeline: RAGPipeline | None = None,
    *,
    default_top_k: int = 3,
    force: bool = False,
) -> None:
    """
    注册 search_knowledge Tool（幂等）。
    """

    global _REGISTERED

    from app.tools.registry import ToolRegistry

    if _REGISTERED and not force:

        return

    ToolRegistry.register(
        SearchKnowledgeTool(
            pipeline=pipeline,
            default_top_k=default_top_k,
        )
    )

    _REGISTERED = True


def reset_search_knowledge_tool_registration() -> None:
    """
    测试用：清除注册状态并从 Registry 移除 Tool。
    """

    global _REGISTERED

    from app.tools.registry import ToolRegistry

    ToolRegistry._tools.pop("search_knowledge", None)

    _REGISTERED = False
