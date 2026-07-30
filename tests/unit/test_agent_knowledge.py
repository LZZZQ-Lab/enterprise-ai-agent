"""Agent 通过 search_knowledge Tool 回答企业文档问题。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.types import AgentContext
from app.config import AgentConfig
from app.embedding.fake import FakeEmbedding
from app.llm.types import ChatResult
from app.llm.types import ToolCall
from app.rag.pipeline import create_rag_pipeline
from app.tools.knowledge_tool import register_search_knowledge_tool
from app.tools.knowledge_tool import reset_search_knowledge_tool_registration
from app.tools.registry import ToolRegistry
from app.vectorstore.manager import create_vector_store

from tests.fixtures.paths import KNOWLEDGE_FIXTURES

FIXTURES = KNOWLEDGE_FIXTURES


@pytest.fixture
def knowledge_pipeline():
    """带已入库样例文档的 RAG Pipeline。"""

    embedding = FakeEmbedding(dimension=64)

    pipeline = create_rag_pipeline(
        embedding_provider=embedding,
        vector_store=create_vector_store(
            "memory",
            dimension=embedding.dimension,
        ),
        top_k=3,
    )

    pipeline.ingest_file(FIXTURES / "sample.txt")

    return pipeline


@pytest.fixture(autouse=True)
def _knowledge_tool_registry(
    knowledge_pipeline,
) -> None:
    """每个测试注册独立 Pipeline 的 search_knowledge。"""

    reset_search_knowledge_tool_registration()

    register_search_knowledge_tool(
        pipeline=knowledge_pipeline,
        force=True,
    )

    yield

    reset_search_knowledge_tool_registration()


class KnowledgeToolMockLLM:
    """
    第一轮调用 search_knowledge，第二轮基于 Tool 结果回答。
    """

    def __init__(self) -> None:

        self._round = 0
        self.bind_tool_manager = lambda tool_manager: None

    def chat(
        self,
        messages,
        use_tools=True,
    ) -> ChatResult:

        self._round += 1

        if self._round == 1:

            return ChatResult(
                model="mock",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call-kb-1",
                        name="search_knowledge",
                        arguments={
                            "query": "产品名称",
                        },
                    )
                ],
            )

        last_tool_content = ""

        for message in reversed(messages):

            if message.role == "tool":

                last_tool_content = message.content or ""

                break

        assert "Enterprise AI Agent Platform" in last_tool_content

        return ChatResult(
            model="mock",
            content=(
                "根据企业知识库，产品名称是 "
                "Enterprise AI Agent Platform。"
            ),
        )


def test_search_knowledge_tool_registered(
    knowledge_pipeline,
) -> None:

    tool = ToolRegistry.get("search_knowledge")

    result = tool.execute(
        __import__(
            "app.tools.types",
            fromlist=["ToolContext"],
        ).ToolContext(
            tool_name="search_knowledge",
            arguments={"query": "RAG 知识库"},
        )
    )

    assert result.success
    assert "Enterprise AI Agent Platform" in result.content


def test_agent_answers_enterprise_document_question(
    knowledge_pipeline,
) -> None:

    from app.agents.chat_agent import ChatAgent

    config = AgentConfig(
        max_iterations=5,
        enable_mcp=False,
        enable_rag=False,
        enable_knowledge_tool=True,
        enable_trace=False,
        enable_planner=False,
        top_k=3,
    )

    agent = ChatAgent(
        config=config,
        client=KnowledgeToolMockLLM(),
    )

    schemas = agent.tool_manager.get_schemas()
    tool_names = [
        schema["function"]["name"]
        for schema in schemas
        if schema.get("type") == "function"
    ]

    assert "search_knowledge" in tool_names

    result = agent.execute(
        AgentContext(
            session_id="kb-test",
            user_message="我们公司的产品名称是什么？",
        )
    )

    assert result.success is True
    assert "Enterprise AI Agent Platform" in (result.content or "")
