from app.memory.factory import get_memory
from app.memory.memory_manager import EnterpriseMemoryManager
from app.memory.memory_manager import get_default_enterprise_memory_manager
from app.memory.types import MemoryContext
from app.memory.types import MemoryRecord


class MemoryManager:
    """
    兼容 Task 1.x 的 MemoryManager；内部双写 Conversation Memory。
    """

    def __init__(
        self,
        enterprise: EnterpriseMemoryManager | None = None,
    ) -> None:

        self.memory = get_memory()
        self.enterprise = enterprise or get_default_enterprise_memory_manager()

    def load(
        self,
        session_id: str,
    ) -> MemoryContext:

        legacy = self.memory.load(session_id)
        merged = self.enterprise.load_merged(session_id)

        if not merged.records:
            return legacy

        return merged

    def save_user_message(
        self,
        session_id: str,
        content: str,
    ) -> None:

        record = MemoryRecord(
            role="user",
            content=content,
        )

        self.memory.save(
            session_id,
            record,
        )
        self.enterprise.save_user_message(session_id, content)

    def save_assistant_message(
        self,
        session_id: str,
        content: str,
    ) -> None:

        record = MemoryRecord(
            role="assistant",
            content=content,
        )

        self.memory.save(
            session_id,
            record,
        )
        self.enterprise.save_assistant_message(session_id, content)

    def clear(
        self,
        session_id: str,
    ) -> None:

        self.memory.clear(session_id)
        self.enterprise.clear_session(session_id)
