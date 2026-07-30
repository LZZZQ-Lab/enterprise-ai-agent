"""
Prompt 存储与注册（Task 6.5）。
"""

from __future__ import annotations

import threading
from pathlib import Path

from app.prompts.context import load_template
from app.prompts.version import PromptVersion
from app.prompts.version import extract_variables
from app.prompts.version import latest_version

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

PROMPT_BASE = "software_team.base"
PROMPT_DEVELOPER = "software_team.developer"
PROMPT_REVIEWER = "software_team.reviewer"
PROMPT_TESTER = "software_team.tester"


class PromptRepository:
    """
    内存 Prompt 仓库，支持多版本与继承链解析。
    """

    def __init__(self) -> None:
        self._versions: dict[str, dict[str, PromptVersion]] = {}
        self._lock = threading.RLock()

    def register(self, prompt: PromptVersion, *, overwrite: bool = False) -> None:
        with self._lock:
            bucket = self._versions.setdefault(prompt.prompt_id, {})

            if prompt.version in bucket and not overwrite:
                raise ValueError(
                    f"Prompt {prompt.prompt_id}@{prompt.version} already exists"
                )

            variables = prompt.variables or extract_variables(prompt.content)
            bucket[prompt.version] = PromptVersion(
                prompt_id=prompt.prompt_id,
                version=prompt.version,
                content=prompt.content,
                role=prompt.role,
                parent_id=prompt.parent_id,
                parent_version=prompt.parent_version,
                description=prompt.description,
                variables=variables,
                metadata=dict(prompt.metadata),
                created_at=prompt.created_at,
            )

    def get(
        self,
        prompt_id: str,
        version: str | None = None,
    ) -> PromptVersion:
        with self._lock:
            bucket = self._versions.get(prompt_id)

            if not bucket:
                raise KeyError(f"Unknown prompt_id: {prompt_id}")

            resolved = version or latest_version(list(bucket.keys()))
            item = bucket.get(resolved)

            if item is None:
                raise KeyError(
                    f"Prompt {prompt_id} version {resolved} not found"
                )

            return item

    def list_versions(self, prompt_id: str) -> list[str]:
        with self._lock:
            bucket = self._versions.get(prompt_id, {})
            return sorted(bucket.keys(), key=lambda v: PromptVersion(
                prompt_id=prompt_id,
                version=v,
                content="",
            ).semver_key())

    def resolve_content(
        self,
        prompt_id: str,
        version: str | None = None,
        *,
        _stack: set[str] | None = None,
    ) -> str:
        """
        解析 Prompt 正文（含继承链：父版本在前，子版本在后）。
        """

        stack = set(_stack or ())

        if prompt_id in stack:
            raise ValueError(f"Prompt inheritance cycle: {prompt_id}")

        stack.add(prompt_id)
        item = self.get(prompt_id, version)
        parts: list[str] = []

        if item.parent_id:
            parent_ver = item.parent_version
            parts.append(
                self.resolve_content(
                    item.parent_id,
                    parent_ver,
                    _stack=stack,
                )
            )

        parts.append(item.content.strip())
        return "\n\n---\n\n".join(part for part in parts if part)

    def register_software_team_defaults(self) -> None:
        """
        从 templates/ 注册 Developer / Reviewer / Tester 及基类角色模板。
        """

        base_content = (
            "你是企业 AI 软件团队成员。\n"
            "遵循安全、可维护性与可测试性原则；输出简洁、可执行。"
        )

        self.register(
            PromptVersion(
                prompt_id=PROMPT_BASE,
                version="1.0.0",
                content=base_content,
                role="team",
                description="Software team 角色基类",
            ),
            overwrite=True,
        )

        mapping = [
            (
                PROMPT_DEVELOPER,
                "developer",
                "software_team_developer.txt",
                "1.0.0",
            ),
            (
                PROMPT_REVIEWER,
                "reviewer",
                "software_team_reviewer.txt",
                "1.0.0",
            ),
            (
                PROMPT_TESTER,
                "tester",
                "software_team_tester.txt",
                "1.0.0",
            ),
        ]

        for prompt_id, role, filename, ver in mapping:
            content = load_template(filename)

            if not content:
                content = (TEMPLATES_DIR / filename).read_text(
                    encoding="utf-8",
                ).strip()

            self.register(
                PromptVersion(
                    prompt_id=prompt_id,
                    version=ver,
                    content=content,
                    role=role,
                    parent_id=PROMPT_BASE,
                    parent_version="1.0.0",
                    description=f"{role} agent template from {filename}",
                ),
                overwrite=True,
            )


_default_repository: PromptRepository | None = None
_repo_lock = threading.Lock()


def get_default_prompt_repository() -> PromptRepository:
    global _default_repository

    with _repo_lock:
        if _default_repository is None:
            repo = PromptRepository()
            repo.register_software_team_defaults()
            _default_repository = repo

        return _default_repository
