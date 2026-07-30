"""Task 5.3 Architecture Agent tests."""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.architecture_agent import ArchitectureAgent
from app.agents.software_team.architecture_agent import _has_required_sections
from app.agents.software_team.architecture_prompt import ARCHITECTURE_TEMPLATE_NAME
from app.agents.software_team.architecture_prompt import (
    fetch_architecture_knowledge,
)
from app.agents.software_team.architecture_prompt import (
    render_architecture_template,
)
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.prompts.context import load_template


class MockKnowledgeRetriever:
    def retrieve(self, query, top_k=3, score_threshold=0.0):
        from app.rag.types import Document
        from app.rag.types import ScoredDocument

        return [
            ScoredDocument(
                document=Document(
                    id="k1",
                    content="企业标准：使用 PostgreSQL。",
                    metadata={"source": "kb"},
                ),
                score=0.85,
            )
        ]


class MockArchLLM:
    model = "mock-arch"

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        return ChatResult(
            model=self.model,
            content=(
                "# System Design\n\n## 系统架构\n\nA\n\n"
                "## 技术选型\n\nT\n\n## 数据库设计\n\nD\n\n"
                "## 接口设计\n\nI\n"
            ),
        )


SAMPLE_PRD = """# PRD

## 功能需求
库存管理

## 用户角色
管理员

## 业务流程
入库出库

## API需求
GET /items
"""


def test_architecture_template_exists() -> None:

    text = load_template(ARCHITECTURE_TEMPLATE_NAME)

    assert "数据库设计" in text
    assert "{prd_content}" in text


def test_render_architecture_template() -> None:

    prompt = render_architecture_template(
        prd_content=SAMPLE_PRD,
        knowledge_context="规范 X",
    )

    assert "库存管理" in prompt
    assert "规范 X" in prompt


def test_architecture_rag() -> None:

    config = AgentConfig(enable_rag=True)

    knowledge, hits = fetch_architecture_knowledge(
        SAMPLE_PRD,
        config=config,
        retriever=MockKnowledgeRetriever(),
    )

    assert hits
    assert "PostgreSQL" in knowledge


def test_architecture_agent_generates_document() -> None:

    agent = ArchitectureAgent(
        config=AgentConfig(enable_rag=True, enable_trace=False),
        client=MockArchLLM(),
        retriever=MockKnowledgeRetriever(),
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message=SAMPLE_PRD,
        )
    )

    assert result.success
    assert _has_required_sections(agent.last_document)


def test_writes_architecture_md(tmp_path: Path) -> None:

    agent = ArchitectureAgent(
        config=AgentConfig(enable_rag=False, enable_trace=False),
        client=MockArchLLM(),
    )

    agent.run(
        AgentContext(
            session_id="t",
            user_message=SAMPLE_PRD,
            metadata={"artifact_dir": str(tmp_path)},
        )
    )

    target = tmp_path / "docs" / "architecture.md"

    assert target.is_file()
    text = target.read_text(encoding="utf-8")

    assert "系统架构" in text
