"""Terminal Tool 执行策略（pytest / devops）。"""

from __future__ import annotations

from contextvars import ContextVar

terminal_mode_ctx: ContextVar[str] = ContextVar(
    "terminal_mode_ctx",
    default="pytest",
)

MODES = frozenset({"pytest", "devops"})
