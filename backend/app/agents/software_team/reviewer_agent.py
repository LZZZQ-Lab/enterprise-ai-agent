"""
Phase 5.5：Reviewer Agent — Git Diff → Review Report。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.software_team.review_report import ReviewReport
from app.agents.software_team.reviewer_heuristics import analyze_diff_heuristics
from app.agents.software_team.reviewer_heuristics import llm_report_has_sections
from app.agents.software_team.reviewer_prompt import REVIEW_REPORT_FILENAME
from app.agents.software_team.reviewer_prompt import fetch_review_standards
from app.agents.software_team.reviewer_prompt import render_reviewer_template
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class ReviewerLLMClient(Protocol):
    model: str

    def chat(self, messages, use_tools: bool = True): ...


class ReviewerAgent(BaseAgent):
    """
    输入 Git Diff →（可选 RAG 规范）→ LLM / 启发式 → Review Report。
    """

    ARTIFACT_RELATIVE_PATH = f"docs/{REVIEW_REPORT_FILENAME}"

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: ReviewerLLMClient | None = None,
        retriever: Any | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client
        self._retriever = retriever

        self.last_report: ReviewReport | None = None
        self.last_report_markdown: str = ""
        self.last_rag_hits: list[Any] = []

    @property
    def name(self) -> str:

        return "reviewer"

    def get_capabilities(self) -> list[str]:

        caps = [
            "software_team",
            "code_review",
        ]

        if self._config.enable_rag:

            caps.append("rag")

        return caps

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        git_diff = self._resolve_git_diff(context)

        if not git_diff:

            return AgentResult(
                success=False,
                model="reviewer",
                content="Empty git diff input.",
            )

        architecture = self._resolve_architecture(context)

        standards, hits = fetch_review_standards(
            git_diff,
            config=self._config,
            retriever=self._retriever,
        )

        self.last_rag_hits = hits

        if self._client is None:

            report = analyze_diff_heuristics(
                git_diff,
                architecture_excerpt=architecture,
            )

            markdown = report.to_markdown()
            model = "heuristic_fallback"

        else:

            from app.llm.types import Message

            prompt = render_reviewer_template(
                git_diff=git_diff,
                architecture_excerpt=architecture,
                standards_context=standards,
            )

            result = self._client.chat(
                [Message(role="user", content=prompt)],
                use_tools=False,
            )

            markdown = (result.content or "").strip()
            model = getattr(result, "model", "reviewer")

            if not markdown or not llm_report_has_sections(markdown):

                report = analyze_diff_heuristics(
                    git_diff,
                    architecture_excerpt=architecture,
                )

                markdown = report.to_markdown()
                model = "heuristic_fallback"

            else:

                report = ReviewReport(
                    summary=_extract_summary(markdown),
                    diff_stats=_diff_stats(git_diff),
                )

        self.last_report = report
        self.last_report_markdown = markdown

        artifact_note = self._maybe_write_report(context, markdown)

        prefix = f"{artifact_note}\n\n" if artifact_note else ""

        return AgentResult(
            success=True,
            model=model,
            content=prefix + markdown,
        )

    def _maybe_write_report(
        self,
        context: AgentContext,
        markdown: str,
    ) -> str:

        artifact_dir = context.metadata.get("artifact_dir")

        if not artifact_dir:

            return ""

        target = Path(str(artifact_dir)) / self.ARTIFACT_RELATIVE_PATH

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")

        return f"Review Report 已写入：`{target.resolve()}`"

    @staticmethod
    def _resolve_git_diff(context: AgentContext) -> str:

        for key in ("git_diff", "diff", "patch"):

            if context.metadata.get(key):

                return str(context.metadata[key]).strip()

            if context.shared_context.get(key):

                return str(context.shared_context[key]).strip()

        diff_path = (
            context.metadata.get("git_diff_path")
            or context.shared_context.get("git_diff_path")
        )

        if diff_path:

            path = Path(str(diff_path))

            if path.is_file():

                return path.read_text(encoding="utf-8")

        workspace = context.metadata.get("workspace_dir") or context.shared_context.get(
            "workspace_dir"
        )

        if workspace and context.metadata.get("use_git_diff"):

            return _load_git_diff_from_repo(Path(str(workspace)))

        return context.user_message.strip()

    @staticmethod
    def _resolve_architecture(context: AgentContext) -> str:

        for key in ("architecture", "architecture_md"):

            if context.shared_context.get(key):

                return str(context.shared_context[key])

            if context.metadata.get(key):

                return str(context.metadata[key])

        workspace = context.metadata.get("workspace_dir") or context.shared_context.get(
            "workspace_dir"
        )

        if workspace:

            doc = Path(str(workspace)) / "docs" / "architecture.md"

            if doc.is_file():

                return doc.read_text(encoding="utf-8")[:8000]

        return ""


def _load_git_diff_from_repo(workspace: Path) -> str:

    import subprocess

    try:

        completed = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if completed.returncode == 0 and completed.stdout.strip():

            return completed.stdout

        completed = subprocess.run(
            ["git", "diff"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        return completed.stdout or ""

    except (OSError, subprocess.SubprocessError):

        return ""


def _extract_summary(markdown: str) -> str:

    if "## 摘要" in markdown:

        part = markdown.split("## 摘要", 1)[1]

        for heading in ("## 代码规范", "## Diff", "## 安全问题"):

            if heading in part:

                part = part.split(heading, 1)[0]

                break

        return part.strip()[:500]

    return markdown[:300]


def _diff_stats(git_diff: str) -> str:

    lines = git_diff.splitlines()
    added = sum(
        1
        for line in lines
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1
        for line in lines
        if line.startswith("-") and not line.startswith("---")
    )

    return f"- 新增行: {added}\n- 删除行: {removed}\n- 总行数: {len(lines)}"
