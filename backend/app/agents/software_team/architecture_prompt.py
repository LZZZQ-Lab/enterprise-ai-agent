"""
Phase 5.3：Architecture Prompt 模板与 Knowledge RAG。
"""

from __future__ import annotations

from typing import Any

from app.agents.software_team.prd_prompt import RetrieverLike
from app.agents.software_team.prd_prompt import format_prompt_template
from app.config import AgentConfig
from app.prompts.context import load_template
from app.rag.context_builder import RAGContextBuilder

ARCHITECTURE_TEMPLATE_NAME = "software_team_architecture.txt"

ARCHITECTURE_ARTIFACT_FILENAME = "architecture.md"

ARCHITECTURE_RAG_QUERY_SUFFIX = (
    "系统架构 数据库设计 技术选型 接口设计 "
    "微服务 部署 企业架构规范"
)


def render_architecture_template(
    *,
    prd_content: str,
    project_name: str = "",
    goal_summary: str = "",
    knowledge_context: str = "",
) -> str:

    template = load_template(ARCHITECTURE_TEMPLATE_NAME)

    if not template:

        raise FileNotFoundError(
            f"Missing prompt template: {ARCHITECTURE_TEMPLATE_NAME}"
        )

    values = {
        "prd_content": prd_content.strip(),
        "project_name": project_name.strip() or "（未命名项目）",
        "goal_summary": goal_summary.strip() or "（未提供）",
        "knowledge_context": knowledge_context.strip()
        or "（未检索到架构知识库条目，请遵循云原生与分层架构最佳实践。）",
    }

    return format_prompt_template(template, values)


def fetch_architecture_knowledge(
    prd_content: str,
    *,
    config: AgentConfig,
    retriever: RetrieverLike | None,
) -> tuple[str, list[Any]]:

    if not config.enable_rag or retriever is None:

        return "", []

    snippet = prd_content.strip()[:1500]

    query = f"{snippet}\n{ARCHITECTURE_RAG_QUERY_SUFFIX}"

    results = retriever.retrieve(
        query=query,
        top_k=config.top_k,
        score_threshold=config.score_threshold,
    )

    if not results:

        return "", []

    text = RAGContextBuilder(
        instruction=(
            "以下为与企业架构、技术栈、数据库与接口规范相关的知识，"
            "设计时必须参考。"
        )
    ).build_context_text(results)

    return text, list(results)
