"""
Agent Studio 内存索引（Task 6.8）。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.workflow.executor import WorkflowExecutor


@dataclass
class StudioSession:
    session_id: str
    project_id: str = ""
    last_workflow_run_id: str = ""
    last_trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class StudioStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, StudioSession] = {}
        self._prompt_overrides: dict[tuple[str, str], str] = {}
        self._executor: WorkflowExecutor | None = None

    def bind_executor(self, executor: WorkflowExecutor) -> None:
        with self._lock:
            self._executor = executor

    @property
    def workflow_executor(self) -> WorkflowExecutor | None:
        return self._executor

    def touch_session(
        self,
        session_id: str,
        *,
        project_id: str = "",
        run_id: str = "",
        trace_id: str = "",
    ) -> StudioSession:
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                session = StudioSession(session_id=session_id)
                self._sessions[session_id] = session

            if project_id:
                session.project_id = project_id

            if run_id:
                session.last_workflow_run_id = run_id

            if trace_id:
                session.last_trace_id = trace_id

            return session

    def get_session(self, session_id: str) -> StudioSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def set_prompt_override(
        self,
        prompt_id: str,
        version: str,
        content: str,
    ) -> None:
        with self._lock:
            self._prompt_overrides[(prompt_id, version)] = content

    def get_prompt_override(
        self,
        prompt_id: str,
        version: str,
    ) -> str | None:
        with self._lock:
            return self._prompt_overrides.get((prompt_id, version))


default_studio_store = StudioStore()
