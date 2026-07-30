"""
Task 1.1 结构重构 - import 兼容测试。

运行:
    cd backend
    python -m app.config.tests.test_task11_structure
"""

from __future__ import annotations


def test_config_new_paths() -> None:

    from app.config import AgentConfig
    from app.config import Settings
    from app.config import get_settings
    from app.config import settings

    assert Settings is not None
    assert AgentConfig is not None
    assert get_settings() is not None
    assert settings is not None


def test_config_legacy_shims() -> None:

    from app.config import Settings
    from app.config import get_settings
    from app.config import settings
    from app.config import AgentConfig
    from app.config import DEFAULT_SYSTEM_PROMPT_PATH

    assert Settings is not None
    assert AgentConfig is not None
    assert DEFAULT_SYSTEM_PROMPT_PATH.name == "system.txt"


def test_prompts_new_paths() -> None:

    from app.prompts import PromptBuilder
    from app.prompts.builder import PromptBuilder as BuilderAlias

    assert PromptBuilder is BuilderAlias


def test_prompts_legacy_path() -> None:

    from app.prompts.builder import PromptBuilder

    assert PromptBuilder is not None


def test_agents_runtime_skeleton() -> None:

    from app.agents.executor import AgentConfig
    from app.agents.executor import AgentExecutor
    from app.agents.executor import PromptBuilder

    assert AgentExecutor is not None
    assert AgentConfig is not None
    assert PromptBuilder is not None


def test_runtime_package_exports() -> None:

    from app.agents.executor import AgentExecutor
    from app.agents.executor import AgentConfig
    from app.agents.executor import PromptBuilder

    assert AgentExecutor is not None
    assert AgentConfig is not None
    assert PromptBuilder is not None


def run_all_tests() -> None:

    test_config_new_paths()
    test_config_legacy_shims()
    test_prompts_new_paths()
    test_prompts_legacy_path()
    test_agents_runtime_skeleton()
    test_runtime_package_exports()

    print("Task 1.1 structure tests passed.")


if __name__ == "__main__":

    run_all_tests()
