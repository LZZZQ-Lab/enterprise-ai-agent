"""
Task 4.6 / Task 8.7：请求上下文（转发至 observability.logging）。
"""

from __future__ import annotations

from observability.logging.context import clear_context
from observability.logging.context import generate_request_id
from observability.logging.context import get_log_context
from observability.logging.context import get_request_id
from observability.logging.context import get_session_id
from observability.logging.context import get_trace_id
from observability.logging.context import set_request_id
from observability.logging.context import set_session_id
from observability.logging.context import set_trace_id

__all__ = [
    "clear_context",
    "generate_request_id",
    "get_log_context",
    "get_request_id",
    "get_session_id",
    "get_trace_id",
    "set_request_id",
    "set_session_id",
    "set_trace_id",
]
