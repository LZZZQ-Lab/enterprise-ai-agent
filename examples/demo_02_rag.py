#!/usr/bin/env python3
"""
Demo 02 — 知识库问答（RAG Pipeline）

流程: 导入样例文档 → 向量检索 → LLM 生成答案与来源。

默认 Mock：FakeEmbedding + InMemory VectorStore + DemoRAGLLM。

用法:
    python examples/demo_02_rag.py
    python examples/demo_02_rag.py --live   # LLM 走真实 Provider
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import REPO_ROOT, bootstrap


def _sample_doc() -> Path:
    return (
        REPO_ROOT
        / "examples"
        / "enterprise_knowledge_assistant"
        / "sample_docs"
        / "platform_intro.md"
    )


def _build_pipeline(*, live: bool):
    from app.embedding.fake import FakeEmbedding
    from app.rag.pipeline import create_rag_pipeline
    from app.vectorstore.manager import create_vector_store
    from _mock import DemoRAGLLM

    embedding = FakeEmbedding(dimension=64)
    store = create_vector_store("memory", dimension=embedding.dimension)

    llm = None
    if not live:
        llm = DemoRAGLLM()

    return create_rag_pipeline(
        embedding_provider=embedding,
        vector_store=store,
        llm=llm,
        top_k=3,
        score_threshold=0.0,
    )


def main() -> None:
    bootstrap()

    parser = argparse.ArgumentParser(description="Demo 02 — RAG Pipeline")
    parser.add_argument(
        "--live",
        action="store_true",
        help="问答阶段使用真实 LLM（Embedding 仍为 Fake）",
    )
    args = parser.parse_args()

    mode = "Live LLM" if args.live else "Mock"
    print(f"=== Demo 02: 知识库问答 (RAG) [{mode}] ===\n")

    sample = _sample_doc()
    if not sample.is_file():
        raise SystemExit(f"样例文档不存在: {sample}")

    pipeline = _build_pipeline(live=args.live)

    chunks = pipeline.ingest_file(sample, extra_metadata={"source": "demo"})
    print(f"[1/3] 入库完成: {sample.name} → {chunks} chunks\n")

    question = "平台如何建立企业知识库并检索？"
    print(f"[2/3] 提问: {question}\n")

    answer = pipeline.ask(question)

    print("[3/3] 回答:")
    print(answer.answer)
    print("\n引用来源:")
    for i, src in enumerate(answer.sources, start=1):
        print(f"  [{i}] score={src.score:.4f} · {src.document_id}")
        preview = (src.content or "").replace("\n", " ")[:100]
        print(f"      {preview}...")

    print("\nDone.")


if __name__ == "__main__":
    main()
