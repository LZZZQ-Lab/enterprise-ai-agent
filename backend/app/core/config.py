"""
兼容层：请改用 app.config.settings。

Task 1.1 起，Settings 已迁移至 app.config.settings。
"""

from app.config.settings import Settings
from app.config.settings import get_settings
from app.config.settings import settings

__all__ = [
    "Settings",
    "get_settings",
    "settings",
]
