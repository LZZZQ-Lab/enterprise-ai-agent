"""RAG Pipeline 问答测试：上传文档 + ask。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.embedding.fake import FakeEmbedding
from app.llm.base import BaseLLM
from app.llm.types import ChatResult
from app.llm.types import Message
from app.rag.context_builder import RAGContextBuilder
from app.rag.pipeline import RAGPipeline
from app.rag.pipeline import ask
from app.rag.pipeline import create_rag_pipeline
from app.vectorstore.manager import create_vector_store

from tests.fixtures.paths import KNOWLEDGE_FIXTURES

FIXTURES = KNOWLEDGE_FIXTURES


class StubLLM(BaseLLM):
    """
    测试用 LLM：返回答案并记录收到的 messages。
    """

    def __init__(
        self,
        reply: str = "这是基于企业知识库的回答。",
    ) -> None:

        super().__init__()

        self.reply = reply
        self.last_messages: list[Message] = []

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:

        self.last_messages = messages

        return ChatResult(
            model="stub",
            content=self.reply,
        )


@pytest.fixture
def rag_pipeline() -> RAGPipeline:

    embedding = FakeEmbedding(dimension=64)

    store = create_vector_store(
        "memory",
        dimension=embedding.dimension,
    )

    return create_rag_pipeline(
        embedding_provider=embedding,
        vector_store=store,
        llm=StubLLM(
            reply="平台核心能力包括 RAG 知识库与 Agent 工具调用。"
        ),
        top_k=3,
        score_threshold=0.0,
    )


def test_context_builder_includes_sources() -> None:

    from app.rag.types import Document
    from app.rag.types import ScoredDocument

    builder = RAGContextBuilder()

    scored = [
        ScoredDocument(
            document=Document(
                id="c1",
                content="Enterprise AI Agent Platform",
                metadata={"file_name": "policy.txt"},
            ),
            score=0.91,
        )
    ]

    text = builder.build_context_text(scored)

    assert "policy.txt" in text
    assert "Enterprise AI Agent" in text

    messages = builder.build_messages(
        "平台叫什么？",
        scored,
    )

    assert messages[0].role == "system"
    assert "检索知识" in (messages[0].content or "")
    assert messages[1].content == "平台叫什么？"


def test_ingest_file_and_ask(
    rag_pipeline: RAGPipeline,
) -> None:

    chunk_count = rag_pipeline.ingest_file(
        FIXTURES / "sample.txt"
    )

    assert chunk_count >= 1

    response = rag_pipeline.ask(
        "产品名称是什么？"
    )

    assert response.answer
    assert "RAG" in response.answer or "知识库" in response.answer
    assert response.sources
    assert response.sources[0].metadata.get("file_name") == "sample.txt"
    assert response.question == "产品名称是什么？"


def test_ask_module_function(
    rag_pipeline: RAGPipeline,
    monkeypatch,
) -> None:

    from app.rag import pipeline as rag_pipeline_module

    monkeypatch.setattr(
        rag_pipeline_module,
        "get_rag_pipeline",
        lambda: rag_pipeline,
    )

    rag_pipeline.ingest_file(FIXTURES / "sample.md")

    result = ask("Agent Runtime 是什么？")

    assert result.sources
    assert result.answer
    assert any(
        source.metadata.get("file_name") == "sample.md"
        for source in result.sources
    )


def test_ask_without_documents_still_calls_llm(
    rag_pipeline: RAGPipeline,
) -> None:

    response = rag_pipeline.ask("空库问题")

    assert response.answer
    assert response.sources == []


def test_full_rag_flow_messages_contain_retrieved_knowledge(
    rag_pipeline: RAGPipeline,
) -> None:

    rag_pipeline.ingest_file(FIXTURES / "sample.txt")

    rag_pipeline.ask("Embedding 检索")

    llm = rag_pipeline._llm

    assert isinstance(llm, StubLLM)

    system_content = llm.last_messages[0].content or ""

    assert "Enterprise AI Agent Platform" in system_content
