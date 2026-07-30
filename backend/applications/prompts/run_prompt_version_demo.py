"""
Task 6.5 Prompt Version Demo。

演示：版本注册、继承、变量替换、按角色获取。

运行:
    cd backend
    python -m applications.prompts.run_prompt_version_demo
"""

from __future__ import annotations

from app.prompts.manager import PromptManager
from app.prompts.repository import PROMPT_DEVELOPER
from app.prompts.repository import PromptRepository
from app.prompts.version import PromptVersion


def main() -> None:
    print("Prompt Center — Version Demo (Task 6.5)\n")

    repo = PromptRepository()
    repo.register_software_team_defaults()
    manager = PromptManager(repository=repo)

    print("Registered versions for developer:")
    for ver in manager.list_versions(PROMPT_DEVELOPER):
        meta = manager.get(PROMPT_DEVELOPER, version=ver)
        print(f"  - {ver}  role={meta.role}  parent={meta.parent_id}")

    repo.register(
        PromptVersion(
            prompt_id=PROMPT_DEVELOPER,
            version="2.0.0",
            content=(
                "## Developer Prompt v2\n"
                "Prioritize tests and small commits.\n\n"
                "{architecture_excerpt}\n{task_list_excerpt}\n{dev_instruction}"
            ),
            role="developer",
            parent_id="software_team.base",
            parent_version="1.0.0",
            description="Stricter dev guidance",
        ),
        overwrite=True,
    )

    variables = {
        "architecture_excerpt": "[arch] microservice API",
        "task_list_excerpt": "[tasks] 1. add endpoint",
        "dev_instruction": "[instr] implement POST /login",
    }

    print("\n--- v1.0.0 (excerpt) ---")
    v1 = manager.render(PROMPT_DEVELOPER, version="1.0.0", variables=variables)
    print("\n".join(v1.splitlines()[:8]))
    print("...")

    print("\n--- v2.0.0 (excerpt) ---")
    v2 = manager.render(PROMPT_DEVELOPER, version="2.0.0", variables=variables)
    print("\n".join(v2.splitlines()[:10]))
    print("...")

    print("\n--- render_role('reviewer') snippet ---")
    reviewer = manager.render_role(
        "reviewer",
        variables={
            "git_diff": "+++ b/app/auth.py",
            "architecture_excerpt": "auth module",
            "standards_context": "OWASP ASVS",
        },
    )
    print(reviewer.split("Git Diff")[0][:320], "...")

    print("\nDemo finished.")


if __name__ == "__main__":
    main()
