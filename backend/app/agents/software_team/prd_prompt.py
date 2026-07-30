"""
Phase 5.2：PRD Prompt 模板渲染与 RAG 上下文。
"""

from __future__ import annotations

from typing import Any
from typing import Protocol

from app.config import AgentConfig
from app.prompts.context import load_template
from app.rag.context_builder import RAGContextBuilder

PRD_TEMPLATE_NAME = "software_team_prd.txt"

RAG_QUERY_SUFFIX = (
    "产品需求文档 PRD 企业规范 API 设计 安全 编码规范"
)


class RetrieverLike(Protocol):
    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.0,
    ): ...


def render_prd_template(
    *,
    user_requirement: str,
    project_name: str = "",
    goal_summary: str = "",
    enterprise_standards: str = "",
) -> str:

    template = load_template(PRD_TEMPLATE_NAME)

    if not template:

        raise FileNotFoundError(
            f"Missing prompt template: {PRD_TEMPLATE_NAME}"
        )

    values = {
        "user_requirement": user_requirement.strip(),
        "project_name": project_name.strip() or _default_project_name(
            user_requirement
        ),
        "goal_summary": goal_summary.strip() or "（未提供）",
        "enterprise_standards": enterprise_standards.strip()
        or "（未检索到企业知识库条目，请遵循通用软件工程与 API 设计最佳实践。）",
    }

    return _format_template(template, values)


def fetch_enterprise_standards(
    requirement: str,
    *,
    config: AgentConfig,
    retriever: RetrieverLike | None,
) -> tuple[str, list[Any]]:

    if not config.enable_rag or retriever is None:

        return "", []

    query = f"{requirement.strip()}\n{RAG_QUERY_SUFFIX}"

    results = retriever.retrieve(
        query=query,
        top_k=config.top_k,
        score_threshold=config.score_threshold,
    )

    if not results:

        return "", []

    text = RAGContextBuilder(
        instruction="以下为与 PRD 相关的企业规范片段，撰写 PRD 时必须参考。"
    ).build_context_text(results)

    return text, list(results)


def _default_project_name(requirement: str) -> str:

    text = requirement.strip().replace("\n", " ")

    if len(text) <= 48:

        return text

    return text[:45] + "..."


def _format_template(
    template: str,
    values: dict[str, str],
) -> str:

    class _SafeDict(dict[str, str]):
        def __missing__(self, key: str) -> str:

            return "{" + key + "}"

    return template.format_map(_SafeDict(values))


def format_prompt_template(
    template: str,
    values: dict[str, str],
) -> str:

    return _format_template(template, values)
