"""PromptBuilder 测试。"""

from __future__ import annotations

from app.agents.types import AgentContext
from app.config import AgentConfig
from app.memory.types import MemoryRecord
from app.prompts.builder import PromptBuilder
from app.prompts.context import PromptContext
from app.prompts.context import load_template


def test_load_prompt_templates() -> None:

    system = load_template("system.txt")

    assert system
    assert "enterprise ai assistant" in system.lower()


def test_prompt_context_from_agent_context() -> None:

    context = AgentContext(
        session_id="s1",
        user_message="你好",
        agent_name="chat",
        agent_role="assistant",
    )

    records = [
        MemoryRecord(
            role="user",
            content="之前的对话",
            metadata={},
        ),
        MemoryRecord(
            role="system",
            content="用户偏好中文",
            metadata={"type": "memory"},
        ),
    ]

    prompt_context = PromptContext.from_agent_context(
        context,
        memory_records=records,
        tool_schemas=[
            {
                "type": "function",
                "function": {
                    "name": "time",
                    "description": "Get current time",
                },
            }
        ],
    )

    assert prompt_context.user_message == "你好"
    assert prompt_context.agent_role == "assistant"
    assert len(prompt_context.conversation_records) == 1
    assert len(prompt_context.long_term_memory_records) == 1


def test_prompt_builder_message_structure() -> None:

    builder = PromptBuilder(
        config=AgentConfig(
            system_prompt="SYSTEM_PROMPT_TEST",
        ),
    )

    prompt_context = PromptContext(
        session_id="s2",
        user_message="帮我查时间",
        agent_name="chat",
        agent_role="general assistant",
        memory_records=[
            MemoryRecord(
                role="system",
                content="Prefer concise answers",
                metadata={"type": "memory"},
            ),
        ],
        tool_schemas=[
            {
                "type": "function",
                "function": {
                    "name": "time",
                    "description": "Get current time",
                },
            }
        ],
    )

    messages = builder.build_messages(prompt_context)

    assert messages[0].role == "system"
    assert messages[0].content == "SYSTEM_PROMPT_TEST"

    assert any(
        message.role == "system"
        and "Agent Role: general assistant" in (message.content or "")
        for message in messages
    )

    assert any(
        message.role == "system"
        and "Prefer concise answers" in (message.content or "")
        for message in messages
    )

    assert any(
        message.role == "system"
        and "- time: Get current time" in (message.content or "")
        for message in messages
    )

    assert messages[-1].role == "user"
    assert messages[-1].content == "帮我查时间"
