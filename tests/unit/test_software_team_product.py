"""Task 5.2 Product Requirement Agent tests."""

from __future__ import annotations

from app.agents.software_team.prd_prompt import PRD_TEMPLATE_NAME
from app.agents.software_team.prd_prompt import fetch_enterprise_standards
from app.agents.software_team.prd_prompt import render_prd_template
from app.agents.software_team.product_agent import ProductRequirementAgent
from app.agents.software_team.product_agent import _has_required_sections
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.prompts.context import load_template


class MockRetriever:
    def retrieve(self, query, top_k=3, score_threshold=0.0):
        from app.rag.types import Document
        from app.rag.types import ScoredDocument

        return [
            ScoredDocument(
                document=Document(
                    id="1",
                    content="企业规范：PRD 必须包含 API 清单。",
                    metadata={"source": "std.md"},
                ),
                score=0.9,
            )
        ]


class MockPRDLLM:
    model = "mock-prd"

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        return ChatResult(
            model=self.model,
            content=(
                "# PRD\n\n## 功能需求\n\nF\n\n## 用户角色\n\nR\n\n"
                "## 业务流程\n\nB\n\n## API需求\n\nA\n"
            ),
        )


def test_prd_template_exists() -> None:

    text = load_template(PRD_TEMPLATE_NAME)

    assert "功能需求" in text
    assert "{user_requirement}" in text


def test_render_prd_template() -> None:

    prompt = render_prd_template(
        user_requirement="开发库存系统",
        enterprise_standards="规范 A",
    )

    assert "开发库存系统" in prompt
    assert "规范 A" in prompt


def test_rag_fetch_when_enabled() -> None:

    config = AgentConfig(enable_rag=True, top_k=2)

    standards, hits = fetch_enterprise_standards(
        "博客",
        config=config,
        retriever=MockRetriever(),
    )

    assert hits
    assert "企业规范" in standards


def test_product_agent_full_prd() -> None:

    agent = ProductRequirementAgent(
        config=AgentConfig(enable_rag=True, enable_trace=False),
        client=MockPRDLLM(),
        retriever=MockRetriever(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="开发一个博客系统",
        )
    )

    assert result.success
    assert _has_required_sections(result.content)
    assert agent.last_rag_hits


def test_product_agent_blog_demo() -> None:

    from applications.software_team.run_product_demo import BlogPRDMockLLM

    agent = ProductRequirementAgent(
        config=AgentConfig(enable_rag=False, enable_trace=False),
        client=BlogPRDMockLLM(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message="开发一个博客系统",
        )
    )

    assert "功能需求" in result.content
    assert "API" in result.content
