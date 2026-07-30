"""
企业 Memory 管理器（Task 6.7）。
"""

from __future__ import annotations

import threading
from typing import Any

from app.memory.long_term import KnowledgeMemory
from app.memory.shared_memory import ProjectMemory
from app.memory.shared_memory import SharedMemory
from app.memory.short_term import ShortTermMemory
from app.memory.types import MemoryContext
from app.memory.types import MemoryKind
from app.memory.types import MemoryRecord


class EnterpriseMemoryManager:
    """
    统一调度 Conversation / Project / Shared / Knowledge 四类 Memory。
    """

    def __init__(self) -> None:
        self.conversation = ShortTermMemory()
        self.project = ProjectMemory()
        self.shared = SharedMemory()
        self.knowledge = KnowledgeMemory()

    @staticmethod
    def resolve_project_id(
        *,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        shared_context: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        shared = shared_context or {}

        for key in ("project_id", "run_id", "workflow_run_id"):
            if meta.get(key):
                return str(meta[key])

            if shared.get(key):
                return str(shared[key])

        return session_id

    def save_user_message(self, session_id: str, content: str) -> None:
        self.conversation.append(session_id, role="user", content=content)

    def save_assistant_message(self, session_id: str, content: str) -> None:
        self.conversation.append(session_id, role="assistant", content=content)

    def write_project(
        self,
        project_id: str,
        key: str,
        value: str,
        *,
        agent_name: str = "",
    ) -> None:
        self.project.put(project_id, key, value, agent_name=agent_name)
        self.shared.publish(
            project_id,
            agent_name=agent_name,
            content=f"project:{key} updated",
            message_type="project_memory",
        )

    def load_project_snapshot(self, project_id: str) -> dict[str, str]:
        return self.project.get_all(project_id)

    def sync_project_to_shared_context(
        self,
        project_id: str,
        shared_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        将 Project Memory 注入 Agent shared_context（跨 Agent 可见）。
        """

        snapshot = self.load_project_snapshot(project_id)
        merged = dict(shared_context)
        merged["project_memory"] = snapshot
        merged["project_id"] = project_id

        if snapshot.get("task_list"):
            merged.setdefault("task_list", snapshot["task_list"])

        if snapshot.get("tasks"):
            merged.setdefault("tasks", snapshot["tasks"])

        if snapshot.get("architecture"):
            merged.setdefault("architecture", snapshot["architecture"])

        if snapshot.get("manager_plan"):
            merged.setdefault("manager_plan", snapshot["manager_plan"])

        return merged

    def load_merged(
        self,
        session_id: str,
        *,
        project_id: str | None = None,
        knowledge_scope: str | None = None,
        include_shared: bool = True,
    ) -> MemoryContext:
        """
        合并 Conversation + Project + Shared + Knowledge 供 Prompt / Agent 使用。
        """

        pid = project_id or session_id
        records: list[MemoryRecord] = []

        records.extend(self.conversation.load(session_id).records)
        records.extend(self.project.to_records(pid))

        if include_shared:
            records.extend(self.shared.read(pid))

        if knowledge_scope:
            records.extend(self.knowledge.load(knowledge_scope))

        return MemoryContext(session_id=session_id, records=records)

    def record_software_project(
        self,
        project_id: str,
        *,
        agent_name: str,
        requirement: str,
        task_list_text: str,
        tasks_json: str = "",
    ) -> None:
        self.write_project(
            project_id,
            "requirement",
            requirement,
            agent_name=agent_name,
        )
        self.write_project(
            project_id,
            "task_list",
            task_list_text,
            agent_name=agent_name,
        )

        if tasks_json:
            self.write_project(
                project_id,
                "tasks",
                tasks_json,
                agent_name=agent_name,
            )

        self.write_project(
            project_id,
            "manager_plan",
            task_list_text,
            agent_name=agent_name,
        )

    def clear_session(self, session_id: str, *, project_id: str | None = None) -> None:
        self.conversation.clear(session_id)

        if project_id:
            self.project.clear_project(project_id)
            self.shared.clear(project_id)


_default_manager: EnterpriseMemoryManager | None = None
_manager_lock = threading.Lock()


def get_default_enterprise_memory_manager() -> EnterpriseMemoryManager:
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = EnterpriseMemoryManager()

        return _default_manager
