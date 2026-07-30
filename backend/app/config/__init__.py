"""
统一配置管理入口。

Task 1.5：Settings 为唯一配置源，AgentConfig.from_env() 读取 Agent 配置。
"""

from app.config.agent import AgentConfig
from app.config.agent import DEFAULT_SYSTEM_PROMPT_PATH
from app.config.settings import Settings
from app.config.settings import get_settings
from app.config.settings import reset_settings_cache
from app.config.settings import settings

__all__ = [
    "AgentConfig",
    "DEFAULT_SYSTEM_PROMPT_PATH",
    "Settings",
    "get_settings",
    "reset_settings_cache",
    "settings",
]
