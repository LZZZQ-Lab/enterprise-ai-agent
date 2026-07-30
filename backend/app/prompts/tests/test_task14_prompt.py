"""
Task 1.4 企业级 Prompt 系统测试。

运行:
    cd backend
    python -m app.prompts.tests.test_task14_prompt
"""

from __future__ import annotations

from app.agents.types import AgentContext
from app.config import AgentConfig
from app.memory.types import MemoryRecord
from app.prompts.builder import PromptBuilder
from app.prompts.context import PromptContext
from app.prompts.context import load_template


def test_load_templates() -> None:

    system = load_template("system.txt")
    context_header = load_template("context_header.txt")
    memory_header = load_template("memory_header.txt")
    tools_header = load_template("tools_header.txt")

    assert "enterprise AI assistant" in system
    assert "Agent execution context" in context_header
    assert "memory" in memory_header.lower()
    assert "tools" in tools_header.lower()


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
    assert len(prompt_context.tool_schemas) == 1


def test_prompt_builder_message_order() -> None:

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
                role="user",
                content="hello",
                metadata={},
            ),
            MemoryRecord(
                role="assistant",
                content="hi",
                metadata={},
            ),
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

    assert messages[1].role == "system"
    assert "Agent Role: general assistant" in (messages[1].content or "")

    assert messages[2].role == "system"
    assert "Prefer concise answers" in (messages[2].content or "")

    assert messages[3].role == "user"
    assert messages[3].content == "hello"

    assert messages[4].role == "assistant"
    assert messages[4].content == "hi"

    assert messages[5].role == "system"
    assert "- time: Get current time" in (messages[5].content or "")

    assert messages[-1].role == "user"
    assert messages[-1].content == "帮我查时间"


def test_chat_agent_uses_prompt_builder() -> None:

    from app.agents.chat_agent import ChatAgent

    agent = ChatAgent(config=AgentConfig(max_iterations=1))

    assert agent.prompt_builder is not None
    assert hasattr(agent.prompt_builder, "build")


def run_all_tests() -> None:

    test_load_templates()
    test_prompt_context_from_agent_context()
    test_prompt_builder_message_order()
    test_chat_agent_uses_prompt_builder()

    print("Task 1.4 Prompt system tests passed.")


if __name__ == "__main__":

    run_all_tests()
