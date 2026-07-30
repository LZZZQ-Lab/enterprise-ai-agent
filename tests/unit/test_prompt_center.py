"""Task 6.5 Prompt Center tests."""

from __future__ import annotations

from app.agents.software_team.developer_prompt import render_developer_template
from app.agents.software_team.reviewer_prompt import render_reviewer_template
from app.agents.software_team.tester_prompt import render_tester_template
from app.prompts.manager import PromptManager
from app.prompts.repository import PROMPT_BASE
from app.prompts.repository import PROMPT_DEVELOPER
from app.prompts.repository import PromptRepository
from app.prompts.version import PromptVersion
from app.prompts.version import latest_version


def test_inheritance_includes_base_role() -> None:
    repo = PromptRepository()
    repo.register_software_team_defaults()

    content = repo.resolve_content(PROMPT_DEVELOPER, "1.0.0")

    assert "企业 AI 软件团队成员" in content
    assert "Developer Agent" in content


def test_variable_substitution_via_manager() -> None:
    repo = PromptRepository()
    repo.register_software_team_defaults()
    manager = PromptManager(repository=repo)

    text = manager.render(
        PROMPT_DEVELOPER,
        variables={
            "architecture_excerpt": "ARCH",
            "task_list_excerpt": "TASKS",
            "dev_instruction": "BUILD",
        },
    )

    assert "ARCH" in text
    assert "TASKS" in text
    assert "BUILD" in text
    assert "{architecture_excerpt}" not in text


def test_version_selection_and_upgrade() -> None:
    repo = PromptRepository()
    repo.register_software_team_defaults()

    repo.register(
        PromptVersion(
            prompt_id=PROMPT_DEVELOPER,
            version="2.0.0",
            content=(
                "Developer v2\n{architecture_excerpt}\n"
                "{task_list_excerpt}\n{dev_instruction}"
            ),
            role="developer",
            parent_id=PROMPT_BASE,
            parent_version="1.0.0",
        ),
        overwrite=True,
    )

    versions = repo.list_versions(PROMPT_DEVELOPER)
    assert latest_version(versions) == "2.0.0"

    manager = PromptManager(repository=repo)
    v1 = manager.render(PROMPT_DEVELOPER, version="1.0.0", variables={
        "architecture_excerpt": "a",
        "task_list_excerpt": "b",
        "dev_instruction": "c",
    })
    v2 = manager.render(PROMPT_DEVELOPER, version="2.0.0", variables={
        "architecture_excerpt": "a",
        "task_list_excerpt": "b",
        "dev_instruction": "c",
    })

    assert "Developer v2" in v2
    assert "Developer v2" not in v1


def test_role_render_helpers() -> None:
    repo = PromptRepository()
    repo.register_software_team_defaults()
    manager = PromptManager(repository=repo)

    dev = manager.render_role(
        "developer",
        variables={
            "architecture_excerpt": "x",
            "task_list_excerpt": "y",
            "dev_instruction": "z",
        },
    )
    rev = manager.render_role(
        "reviewer",
        variables={
            "git_diff": "diff",
            "architecture_excerpt": "a",
            "standards_context": "std",
        },
    )
    tst = manager.render_role(
        "tester",
        variables={
            "architecture_excerpt": "a",
            "source_hint": "src",
            "test_instruction": "run tests",
        },
    )

    assert "Developer Agent" in dev
    assert "Reviewer Agent" in rev
    assert "Tester Agent" in tst


def test_agent_prompt_modules_use_prompt_center() -> None:
    dev = render_developer_template(
        architecture_excerpt="A",
        task_list_excerpt="T",
        dev_instruction="D",
    )
    rev = render_reviewer_template(
        git_diff="+ change",
        architecture_excerpt="A",
        standards_context="S",
    )
    tst = render_tester_template(
        architecture_excerpt="A",
        source_hint="src/",
        test_instruction="pytest",
    )

    assert "A" in dev and "D" in dev
    assert "+ change" in rev
    assert "pytest" in tst
