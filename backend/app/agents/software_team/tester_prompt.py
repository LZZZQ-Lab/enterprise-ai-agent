"""
Task 5.6：Tester Prompt 模板。
"""

from __future__ import annotations

from app.agents.software_team.prd_prompt import format_prompt_template
from app.prompts.manager import TESTER_PROMPT_ID
from app.prompts.manager import get_default_prompt_manager

TEST_REPORT_FILENAME = "TEST_REPORT.md"
DEFAULT_PYTEST_CMD = "python -m pytest tests -q --tb=short"


def render_tester_template(
    *,
    architecture_excerpt: str,
    source_hint: str,
    test_instruction: str,
) -> str:

    manager = get_default_prompt_manager()
    template = manager.render(TESTER_PROMPT_ID)

    return format_prompt_template(
        template,
        {
            "architecture_excerpt": architecture_excerpt.strip()
            or "（未提供）",
            "source_hint": source_hint.strip()
            or "（请先 filesystem read src/ 与 docs/architecture.md）",
            "test_instruction": test_instruction.strip()
            or "生成 Unit Test 与 API Test，并用 terminal 运行 pytest",
        },
    )
