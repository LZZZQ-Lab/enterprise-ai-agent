"""向量库 BaseVectorStore / Chroma 插入与查询测试。"""

from __future__ import annotations

import pytest

from app.embedding.fake import FakeEmbedding
from app.knowledge.loader import DocumentLoader
from app.knowledge.splitter import DocumentSplitter
from app.rag.knowledge_base import KnowledgeBase
from app.rag.types import Document
from app.vectorstore.chroma import ChromaVectorStore
from app.vectorstore.manager import create_vector_store


from tests.fixtures.paths import KNOWLEDGE_FIXTURES

FIXTURES = KNOWLEDGE_FIXTURES


def _chunk_documents() -> list[Document]:
    """Loader → Splitter → RAG Document（模拟 Chunk + Embedding 前状态）。"""

    loader = DocumentLoader()
    splitter = DocumentSplitter()

    source = loader.load(FIXTURES / "sample.txt")

    return [
        chunk.to_rag_document()
        for chunk in splitter.split(source)
    ]


@pytest.fixture
def fake_embedding() -> FakeEmbedding:

    return FakeEmbedding(dimension=64)


def test_memory_vector_store_insert_and_search(
    fake_embedding: FakeEmbedding,
) -> None:

    store = create_vector_store(
        "memory",
        dimension=fake_embedding.dimension,
    )

    chunks = _chunk_documents()

    for chunk in chunks:

        vector = fake_embedding.embed_one(chunk.content)
        store.add(chunk, vector)

    query_vector = fake_embedding.embed_one("RAG 知识库")

    hits = store.search(
        query_vector,
        top_k=2,
    )

    assert len(hits) >= 1
    assert hits[0].score > 0
    assert hits[0].document.content


def test_chroma_vector_store_insert(
    fake_embedding: FakeEmbedding,
    tmp_path,
) -> None:

    pytest.importorskip("chromadb")

    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma_insert",
        collection_name="test_insert",
        dimension=fake_embedding.dimension,
    )

    doc = Document(
        id="chunk-insert-1",
        content="企业向量库插入测试内容。",
        metadata={"kb_id": "test", "source": "unit"},
    )

    vector = fake_embedding.embed_one(doc.content)

    store.add(doc, vector)

    hits = store.search(
        fake_embedding.embed_one("插入测试"),
        top_k=1,
    )

    assert hits
    assert hits[0].document.id == doc.id


def test_chroma_vector_store_search(
    fake_embedding: FakeEmbedding,
    tmp_path,
) -> None:

    pytest.importorskip("chromadb")

    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma_search",
        collection_name="test_search",
        dimension=fake_embedding.dimension,
    )

    chunks = _chunk_documents()

    for chunk in chunks:

        store.add(
            chunk,
            fake_embedding.embed_one(chunk.content),
        )

    query = fake_embedding.embed_one("Embedding 检索")

    hits = store.search(query, top_k=3)

    assert hits
    assert all(item.score >= 0 for item in hits)


def test_knowledge_base_pipeline_chunk_embedding_vector_db(
    fake_embedding: FakeEmbedding,
    tmp_path,
) -> None:

    pytest.importorskip("chromadb")

    store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma_pipeline",
        collection_name="test_pipeline",
        dimension=fake_embedding.dimension,
    )

    kb = KnowledgeBase(
        embedding_provider=fake_embedding,
        vector_store=store,
    )

    loader = DocumentLoader()
    splitter = DocumentSplitter()
    root = loader.load(FIXTURES / "sample.md")

    for chunk in splitter.split(root):

        kb.ingest(chunk.to_rag_document())

    results = kb.search(
        query="Agent Runtime",
        top_k=2,
    )

    assert results
    assert "Agent" in results[0].document.content or results[0].score > 0


def test_create_vector_store_unknown() -> None:

    with pytest.raises(ValueError, match="Unknown vector store"):

        create_vector_store("milvus")
