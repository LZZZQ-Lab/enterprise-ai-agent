from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from app.memory.types import MemoryRecord

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class PromptContext:
    """
    Prompt 构建输入上下文。

    聚合用户输入、Memory、Tool 列表、Agent 角色等信息，
    供 PromptBuilder 生成完整 messages。
    """

    session_id: str
    user_message: str
    agent_name: str = ""
    agent_role: str = ""
    memory_records: list[MemoryRecord] = field(default_factory=list)
    tool_schemas: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    shared_context: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[Any] = field(default_factory=list)
    plan: Any | None = None
    current_step: Any | None = None

    @classmethod
    def from_agent_context(
        cls,
        context: Any,
        *,
        memory_records: list[MemoryRecord] | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
        completed_steps: list[Any] | None = None,
    ) -> "PromptContext":

        return cls(
            session_id=context.session_id,
            user_message=context.user_message,
            agent_name=context.agent_name,
            agent_role=context.agent_role,
            memory_records=list(memory_records or context.history or []),
            tool_schemas=list(tool_schemas or []),
            metadata=dict(context.metadata or {}),
            shared_context=dict(context.shared_context or {}),
            completed_steps=list(completed_steps or []),
            plan=context.plan,
            current_step=context.current_step,
        )

    @property
    def conversation_records(self) -> list[MemoryRecord]:

        return [
            record
            for record in self.memory_records
            if record.role in ("user", "assistant")
            and record.metadata.get("type") != "memory"
        ]

    @property
    def long_term_memory_records(self) -> list[MemoryRecord]:

        return [
            record
            for record in self.memory_records
            if record.metadata.get("type") == "memory"
        ]


def load_template(name: str) -> str:
    """
    从 templates/ 目录加载 Prompt 模板。
    """

    path = TEMPLATES_DIR / name

    if not path.is_file():

        return ""

    return path.read_text(encoding="utf-8").strip()
