"""
Task 5.5：Reviewer Prompt 与规范知识 RAG。
"""

from __future__ import annotations

from typing import Any

from app.agents.software_team.prd_prompt import RetrieverLike
from app.agents.software_team.prd_prompt import format_prompt_template
from app.config import AgentConfig
from app.prompts.manager import REVIEWER_PROMPT_ID
from app.prompts.manager import get_default_prompt_manager

from app.rag.context_builder import RAGContextBuilder

REVIEW_REPORT_FILENAME = "REVIEW_REPORT.md"

REVIEW_RAG_QUERY_SUFFIX = (
    "代码审查 代码规范 安全 OWASP 性能 架构 最佳实践"
)


def render_reviewer_template(
    *,
    git_diff: str,
    architecture_excerpt: str = "",
    standards_context: str = "",
) -> str:

    manager = get_default_prompt_manager()
    template = manager.render(REVIEWER_PROMPT_ID)

    return format_prompt_template(
        template,
        {
            "git_diff": _trim_diff(git_diff),
            "architecture_excerpt": architecture_excerpt.strip()
            or "（未提供架构文档，仅基于 Diff 审查）",
            "standards_context": standards_context.strip()
            or "（未检索到企业规范，请使用行业通用标准）",
        },
    )


def fetch_review_standards(
    git_diff: str,
    *,
    config: AgentConfig,
    retriever: RetrieverLike | None,
) -> tuple[str, list[Any]]:

    if not config.enable_rag or retriever is None:

        return "", []

    snippet = git_diff.strip()[:1200]

    query = f"{snippet}\n{REVIEW_RAG_QUERY_SUFFIX}"

    results = retriever.retrieve(
        query=query,
        top_k=config.top_k,
        score_threshold=config.score_threshold,
    )

    if not results:

        return "", []

    text = RAGContextBuilder(
        instruction="以下为代码审查应遵循的企业规范与安全要求。"
    ).build_context_text(results)

    return text, list(results)


def _trim_diff(diff: str, limit: int = 60_000) -> str:

    text = diff.strip()

    if len(text) <= limit:

        return text

    return (
        text[:limit]
        + f"\n\n...[diff truncated, total {len(text)} chars]"
    )
