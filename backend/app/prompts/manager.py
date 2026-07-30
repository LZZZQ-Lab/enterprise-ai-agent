"""
Prompt Center 管理器（Task 6.5）。

统一：版本、变量替换、角色模板、继承。
"""

from __future__ import annotations

import threading

from app.prompts.repository import PROMPT_DEVELOPER
from app.prompts.repository import PROMPT_REVIEWER
from app.prompts.repository import PROMPT_TESTER
from app.prompts.repository import PromptRepository
from app.prompts.repository import get_default_prompt_repository
from app.prompts.version import PromptVersion


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class PromptManager:
    """
    Agent 通过本类获取 Prompt，禁止在 Agent 内写死长 Prompt。
    """

    def __init__(self, repository: PromptRepository | None = None) -> None:
        self._repository = repository or get_default_prompt_repository()

    @property
    def repository(self) -> PromptRepository:
        return self._repository

    def get(
        self,
        prompt_id: str,
        *,
        version: str | None = None,
    ) -> PromptVersion:
        return self._repository.get(prompt_id, version)

    def list_versions(self, prompt_id: str) -> list[str]:
        return self._repository.list_versions(prompt_id)

    def render(
        self,
        prompt_id: str,
        *,
        version: str | None = None,
        variables: dict[str, str] | None = None,
    ) -> str:
        """
        解析继承链并替换 ``{variable}`` 占位符。
        """

        template = self._repository.resolve_content(prompt_id, version)
        return self.substitute_variables(template, variables or {})

    def render_role(
        self,
        role: str,
        *,
        version: str | None = None,
        variables: dict[str, str] | None = None,
    ) -> str:
        """
        按角色名渲染（developer / reviewer / tester）。
        """

        prompt_id = self._role_to_prompt_id(role)
        return self.render(prompt_id, version=version, variables=variables)

    @staticmethod
    def substitute_variables(
        template: str,
        variables: dict[str, str],
    ) -> str:
        normalized = {key: str(value) for key, value in variables.items()}
        return template.format_map(_SafeFormatDict(normalized))

    def register(self, prompt: PromptVersion, *, overwrite: bool = False) -> None:
        self._repository.register(prompt, overwrite=overwrite)

    @staticmethod
    def _role_to_prompt_id(role: str) -> str:
        mapping = {
            "developer": PROMPT_DEVELOPER,
            "reviewer": PROMPT_REVIEWER,
            "tester": PROMPT_TESTER,
        }
        key = role.strip().lower()

        if key not in mapping:
            raise KeyError(f"Unknown prompt role: {role}")

        return mapping[key]


_default_manager: PromptManager | None = None
_manager_lock = threading.Lock()


def get_default_prompt_manager() -> PromptManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = PromptManager()

        return _default_manager


# 便捷常量（供 Agent / Workflow 引用 ID，而非写死正文）
DEVELOPER_PROMPT_ID = PROMPT_DEVELOPER
REVIEWER_PROMPT_ID = PROMPT_REVIEWER
TESTER_PROMPT_ID = PROMPT_TESTER
