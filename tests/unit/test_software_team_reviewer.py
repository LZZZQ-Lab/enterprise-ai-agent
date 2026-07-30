"""Task 5.5 Reviewer Agent tests."""

from __future__ import annotations

from pathlib import Path

from app.agents.software_team.review_report import ReviewReport
from app.agents.software_team.reviewer_agent import ReviewerAgent
from app.agents.software_team.reviewer_heuristics import analyze_diff_heuristics
from app.agents.software_team.reviewer_heuristics import llm_report_has_sections
from app.agents.software_team.reviewer_prompt import render_reviewer_template
from app.agents.types import AgentContext
from app.config import AgentConfig
from app.prompts.manager import REVIEWER_PROMPT_ID
from app.prompts.manager import get_default_prompt_manager


SAMPLE_DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1,3 @@
+password = "x"
+eval(x)
"""


def test_reviewer_template() -> None:

    text = get_default_prompt_manager().render(REVIEWER_PROMPT_ID)

    assert "git_diff" in text or "Git Diff" in text


def test_heuristics_finds_security() -> None:

    report = analyze_diff_heuristics(SAMPLE_DIFF)

    assert any(item.category == "security" for item in report.findings)
    md = report.to_markdown()

    assert "安全问题" in md
    assert "修改建议汇总" in md


def test_llm_section_validator() -> None:

    good = (
        "## 代码规范\n\nok\n\n## 安全问题\n\n## 性能问题\n\n"
        "## 架构问题\n\n## 修改建议汇总\n\n1. fix"
    )

    assert llm_report_has_sections(good)
    assert not llm_report_has_sections("too short")


def test_reviewer_agent_heuristic_mode() -> None:

    agent = ReviewerAgent(
        config=AgentConfig(enable_trace=False),
        client=None,
    )

    result = agent.run(
        AgentContext(
            session_id="t",
            user_message=SAMPLE_DIFF,
            metadata={"git_diff": SAMPLE_DIFF},
        )
    )

    assert result.success
    assert agent.last_report is not None
    assert len(agent.last_report.findings) >= 2


def test_reviewer_writes_report(tmp_path: Path) -> None:

    from app.llm.types import ChatResult

    class MockLLM:
        model = "m"

        def chat(self, messages, use_tools=True):

            return ChatResult(
                model=self.model,
                content=(
                    "# R\n\n## 摘要\n\nok\n\n## 代码规范\n\n-\n\n"
                    "## 安全问题\n\n-\n\n## 性能问题\n\n-\n\n"
                    "## 架构问题\n\n-\n\n## 修改建议汇总\n\n1. a"
                ),
            )

    agent = ReviewerAgent(
        config=AgentConfig(enable_trace=False),
        client=MockLLM(),
    )

    agent.run(
        AgentContext(
            session_id="t",
            user_message=SAMPLE_DIFF,
            metadata={
                "git_diff": SAMPLE_DIFF,
                "artifact_dir": str(tmp_path),
            },
        )
    )

    report_path = tmp_path / "docs" / "REVIEW_REPORT.md"

    assert report_path.is_file()


def test_render_reviewer_template_includes_diff() -> None:

    prompt = render_reviewer_template(
        git_diff="+++ b\n+line",
        standards_context="std",
    )

    assert "+line" in prompt
    assert "std" in prompt
