"""
Task 4.6 / Task 8.7：JSON 结构化日志（转发至 observability.logging）。
"""

from __future__ import annotations

import logging

from observability.logging.logger import STRUCTURED_LOGGER_NAME
from observability.logging.logger import configure_structured_logging
from observability.logging.logger import get_structured_logger
from observability.logging.logger import log_event

__all__ = [
    "STRUCTURED_LOGGER_NAME",
    "configure_structured_logging",
    "get_structured_logger",
    "log_event",
]
