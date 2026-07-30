"""企业知识助手 API 测试。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import AgentConfig
from app.embedding.fake import FakeEmbedding
from app.main import app
from app.rag.pipeline import create_rag_pipeline
from app.services.knowledge_assistant_service import KnowledgeAssistantService
from app.vectorstore.manager import create_vector_store

from tests.fixtures.paths import REPO_ROOT

SAMPLE = (
    REPO_ROOT
    / "examples"
    / "enterprise_knowledge_assistant"
    / "sample_docs"
    / "platform_intro.md"
)


class _KbMockLLM:
    def bind_tool_manager(self, _tool_manager) -> None:

        return None

    def chat(self, messages, use_tools=True):

        from app.llm.types import ChatResult
        from app.llm.types import ToolCall

        for message in reversed(messages):

            if message.role == "tool":

                return ChatResult(
                    model="kb-mock",
                    content=(
                        "平台支持上传文档并经由 "
                        "search_knowledge 检索后回答。"
                    ),
                )

        return ChatResult(
            model="kb-mock",
            content=None,
            tool_calls=[
                ToolCall(
                    id="kb-1",
                    name="search_knowledge",
                    arguments={
                        "query": "文档格式",
                    },
                )
            ],
        )


@pytest.fixture
def kb_client(
    tmp_path,
    monkeypatch,
) -> TestClient:

    embedding = FakeEmbedding(dimension=64)

    pipeline = create_rag_pipeline(
        embedding_provider=embedding,
        vector_store=create_vector_store(
            "memory",
            dimension=embedding.dimension,
        ),
    )

    from app.agents.runtime import AgentRuntime
    from app.tools.knowledge_tool import register_search_knowledge_tool
    from app.tools.knowledge_tool import reset_search_knowledge_tool_registration

    reset_search_knowledge_tool_registration()

    register_search_knowledge_tool(
        pipeline=pipeline,
        force=True,
    )

    runtime = AgentRuntime(
        default_config=AgentConfig(
            max_iterations=5,
            enable_knowledge_tool=True,
            enable_mcp=False,
            enable_trace=False,
            enable_planner=False,
        ),
    )

    service = KnowledgeAssistantService(
        runtime=runtime,
        pipeline=pipeline,
    )

    monkeypatch.setattr(
        "app.api.v1.knowledge.knowledge_assistant_service",
        service,
    )

    original_run = runtime.run

    def run_with_mock(
        task,
        *,
        config=None,
        **agent_kwargs,
    ):

        agent_kwargs.setdefault(
            "client",
            _KbMockLLM(),
        )

        return original_run(
            task,
            config=config,
            **agent_kwargs,
        )

    monkeypatch.setattr(
        runtime,
        "run",
        run_with_mock,
    )

    service._runtime = runtime

    yield TestClient(app)

    reset_search_knowledge_tool_registration()


def test_upload_and_ask_flow(
    kb_client: TestClient,
) -> None:

    assert SAMPLE.is_file()

    upload = kb_client.post(
        "/api/v1/knowledge/documents",
        files={
            "file": (
                "platform_intro.md",
                SAMPLE.read_bytes(),
                "text/markdown",
            )
        },
    )

    assert upload.status_code == 200

    upload_body = upload.json()

    assert upload_body["success"] is True
    assert upload_body["chunks_ingested"] >= 1

    ask = kb_client.post(
        "/api/v1/knowledge/ask",
        json={
            "session_id": "api-test",
            "question": "支持哪些文档格式？",
        },
    )

    assert ask.status_code == 200

    body = ask.json()

    assert body["success"] is True
    assert body["answer"]
    assert body["sources"]
