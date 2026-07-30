"""Developer Agent 工作区 contextvar。"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

developer_workspace_ctx: ContextVar[Path | None] = ContextVar(
    "developer_workspace_ctx",
    default=None,
)
