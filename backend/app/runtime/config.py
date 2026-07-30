"""
兼容层：请改用 app.config.agent。

Task 1.1 起，AgentConfig 已迁移至 app.config.agent。
"""

from app.config.agent import AgentConfig
from app.config.agent import DEFAULT_SYSTEM_PROMPT_PATH

__all__ = [
    "AgentConfig",
    "DEFAULT_SYSTEM_PROMPT_PATH",
]
