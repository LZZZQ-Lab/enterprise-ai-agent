from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.llm.types import Message
from app.memory.manager import MemoryManager
from app.memory.types import MemoryRecord
from app.config import AgentConfig
from app.prompts.context import PromptContext
from app.prompts.context import load_template
from app.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.mcp.prompt_provider import MCPPromptProvider
    from app.mcp.resource import MCPResourceProvider
    from app.rag.retriever import Retriever
    from app.rag.types import ScoredDocument
    from app.agents.executor.tracer import AgentTracer
    from app.tools.manager import ToolManager


class PromptBuilder:
    """
    企业级 Prompt 构建器。

    将 AgentContext 组装为 LLM messages，输出顺序：

    System Prompt → Context → Memory → Tools → User Message

    单一职责：Prompt 拼接，不关心 Agent Loop 或 LLM 调用。
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        system_prompt: str | None = None,
        system_prompt_path: Path | None = None,
        memory_manager: MemoryManager | None = None,
        tool_manager: "ToolManager | None" = None,
        retriever: "Retriever | None" = None,
        mcp_resource_provider: "MCPResourceProvider | None" = None,
        mcp_prompt_provider: "MCPPromptProvider | None" = None,
        tracer: "AgentTracer | None" = None,
    ):

        self._config = config or AgentConfig.from_env()
        self._system_prompt = self._resolve_system_prompt(
            system_prompt,
            system_prompt_path,
        )
        self._memory_manager = memory_manager or MemoryManager()
        self._tool_manager = tool_manager
        self._retriever = retriever
        self._mcp_resource_provider = mcp_resource_provider
        self._mcp_prompt_provider = mcp_prompt_provider
        self._tracer = tracer

        self._context_header = load_template("context_header.txt")
        self._memory_header = load_template("memory_header.txt")
        self._tools_header = load_template("tools_header.txt")

    def build(
        self,
        context: "AgentContext",
        completed_steps: list | None = None,
    ) -> list[Message]:
        """
        从 AgentContext 构建完整 messages（ChatAgent 入口）。
        """

        memory_context = self._memory_manager.load(
            context.session_id,
        )

        records = memory_context.records
        context.history = records

        if self._tracer is not None:

            memory_count = sum(
                1
                for record in records
                if record.metadata.get("type") == "memory"
            )

            self._tracer.on_memory_load(
                session_id=context.session_id,
                record_count=len(records),
                memory_record_count=memory_count,
            )

        prompt_context = PromptContext.from_agent_context(
            context,
            memory_records=records,
            tool_schemas=self._resolve_tool_schemas(),
            completed_steps=completed_steps or [],
        )

        return self.build_messages(prompt_context)

    def build_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:
        """
        从 PromptContext 按企业级顺序构建 messages。
        """

        messages: list[Message] = []

        messages.append(
            self._build_system_prompt_message(),
        )

        messages.extend(
            self._build_context_messages(prompt_context),
        )

        messages.extend(
            self._build_memory_messages(prompt_context),
        )

        messages.extend(
            self._build_history_messages(
                prompt_context.conversation_records,
            ),
        )

        messages.extend(
            self._build_tools_messages(prompt_context),
        )

        messages.append(
            self._build_user_message(prompt_context),
        )

        return messages

    def _resolve_system_prompt(
        self,
        system_prompt: str | None,
        system_prompt_path: Path | None,
    ) -> str:

        if system_prompt is not None:

            return system_prompt

        if self._config.system_prompt is not None:

            return self._config.system_prompt

        if system_prompt_path is not None:

            return system_prompt_path.read_text(encoding="utf-8")

        if self._config.system_prompt_path is not None:

            return self._config.system_prompt_path.read_text(
                encoding="utf-8",
            )

        template_prompt = load_template("system.txt")

        if template_prompt:

            return template_prompt

        return ""

    def _resolve_tool_schemas(self) -> list[dict]:

        if self._tool_manager is not None:

            return self._tool_manager.get_schemas()

        return ToolRegistry.get_schemas()

    def _build_system_prompt_message(self) -> Message:

        return Message(
            role="system",
            content=self._system_prompt,
        )

    def _build_context_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:

        sections: list[str] = []

        sections.extend(
            self._build_agent_role_sections(prompt_context),
        )

        sections.extend(
            self._build_rag_sections(prompt_context.user_message),
        )

        sections.extend(
            self._build_mcp_resource_sections(),
        )

        sections.extend(
            self._build_mcp_prompt_sections(prompt_context),
        )

        sections.extend(
            self._build_plan_sections(prompt_context),
        )

        if not sections:

            return []

        header = self._context_header or "Agent execution context:"

        return [
            Message(
                role="system",
                content=f"{header}\n" + "\n".join(sections),
            )
        ]

    def _build_agent_role_sections(
        self,
        prompt_context: PromptContext,
    ) -> list[str]:

        sections: list[str] = []

        if prompt_context.agent_name:

            sections.append(
                f"Agent Identity: {prompt_context.agent_name}",
            )

        if prompt_context.agent_role:

            sections.append(
                f"Agent Role: {prompt_context.agent_role}",
            )

        current_task = prompt_context.metadata.get("current_task")

        if current_task:

            sections.append(f"Current Task: {current_task}")

        root_goal = prompt_context.metadata.get("root_goal")

        if root_goal:

            sections.append(f"Overall Goal: {root_goal}")

        if prompt_context.shared_context:

            sections.append("Shared Context from other agents:")

            for key, value in prompt_context.shared_context.items():

                preview = str(value)[:300]

                sections.append(f"- {key}: {preview}")

        return sections

    def _build_memory_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:

        memory_records = prompt_context.long_term_memory_records

        if not memory_records:

            return []

        memory_text = "\n".join(
            record.content
            for record in memory_records
        )

        header = self._memory_header or (
            "Relevant memory from previous sessions:"
        )

        return [
            Message(
                role="system",
                content=f"{header}\n{memory_text}",
            )
        ]

    def _build_history_messages(
        self,
        records: list[MemoryRecord],
    ) -> list[Message]:

        return [
            Message(
                role=record.role,
                content=record.content,
            )
            for record in records
        ]

    def _build_tools_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:

        if not prompt_context.tool_schemas:

            return []

        tool_lines: list[str] = []

        for schema in prompt_context.tool_schemas:

            function = schema.get("function", schema)
            name = function.get("name", "unknown")
            description = function.get("description", "")
            tool_lines.append(f"- {name}: {description}")

        header = self._tools_header or "Available tools (call when needed):"

        return [
            Message(
                role="system",
                content=f"{header}\n" + "\n".join(tool_lines),
            )
        ]

    def _build_user_message(
        self,
        prompt_context: PromptContext,
    ) -> Message:

        return Message(
            role="user",
            content=prompt_context.user_message,
        )

    def _build_rag_sections(
        self,
        query: str,
    ) -> list[str]:

        rag_messages = self._build_rag_messages(query)

        if not rag_messages:

            return []

        content = rag_messages[0].content or ""

        return [content]

    def _build_rag_messages(
        self,
        query: str,
    ) -> list[Message]:

        if not self._config.enable_rag:

            return []

        if self._retriever is None:

            return []

        results = self._retriever.retrieve(
            query=query,
            top_k=self._config.top_k,
            score_threshold=self._config.score_threshold,
        )

        if not results:

            if self._tracer is not None:

                self._tracer.on_rag_retrieval(
                    query,
                    results,
                    embedding_provider=self._embedding_provider_name(),
                    top_k=self._config.top_k,
                    injected_content="",
                )

            return []

        rag_message = self._format_rag_message(results)

        if self._tracer is not None:

            self._tracer.on_rag_retrieval(
                query,
                results,
                embedding_provider=self._embedding_provider_name(),
                top_k=self._config.top_k,
                injected_content=rag_message.content or "",
            )

        return [rag_message]

    def _build_mcp_resource_sections(self) -> list[str]:

        messages = self._build_mcp_resource_messages()

        if not messages:

            return []

        return [messages[0].content or ""]

    def _build_mcp_resource_messages(
        self,
    ) -> list[Message]:

        if not self._config.enable_mcp:

            return []

        if not self._config.auto_discover_resources:

            return []

        if self._mcp_resource_provider is None:

            return []

        resources = self._mcp_resource_provider.list_resources()

        if not resources:

            return []

        sections: list[str] = []

        for resource in resources:

            content = self._mcp_resource_provider.read_resource(
                resource.id,
            )

            if self._tracer is not None:

                self._tracer.on_mcp_resource(
                    server_name=resource.server_name,
                    resource_id=resource.id,
                    content_preview=content.content,
                )

            sections.append(
                f"[{resource.name}] "
                f"({resource.description})\n"
                f"{content.content}",
            )

        return [
            Message(
                role="system",
                content=(
                    "The following MCP resources may help "
                    "answer the user's question:\n\n"
                    + "\n\n".join(sections)
                ),
            )
        ]

    def _build_mcp_prompt_sections(
        self,
        prompt_context: PromptContext,
    ) -> list[str]:

        messages = self._build_mcp_prompt_messages(prompt_context)

        return [
            message.content or ""
            for message in messages
            if message.content
        ]

    def _build_mcp_prompt_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:

        if not self._config.enable_mcp:

            return []

        if not self._config.enable_mcp_prompts:

            return []

        if self._mcp_prompt_provider is None:

            return []

        prompt_name = self._config.mcp_prompt_name

        if not prompt_name:

            return []

        prompt_result = self._mcp_prompt_provider.get_prompt(
            name=prompt_name,
            arguments={
                "topic": prompt_context.user_message,
            },
        )

        if self._tracer is not None:

            if "." in prompt_name:

                server_name, name = prompt_name.split(
                    ".",
                    maxsplit=1,
                )

            else:

                server_name = "unknown"
                name = prompt_name

            self._tracer.on_mcp_prompt(
                server_name=server_name,
                prompt_name=name,
            )

        return [
            Message(
                role=message.role,
                content=message.content,
            )
            for message in prompt_result.messages
        ]

    def _build_plan_sections(
        self,
        prompt_context: PromptContext,
    ) -> list[str]:

        messages = self._build_plan_messages(prompt_context)

        if not messages:

            return []

        return [messages[0].content or ""]

    def _build_plan_messages(
        self,
        prompt_context: PromptContext,
    ) -> list[Message]:

        plan = prompt_context.plan

        if plan is None:

            return []

        sections: list[str] = [
            f"Goal: {plan.goal}",
            f"Plan status: {plan.status.value}",
        ]

        if prompt_context.current_step is not None:

            sections.append(
                "Current step "
                f"[{prompt_context.current_step.id}]: "
                f"{prompt_context.current_step.description}",
            )

            if prompt_context.current_step.tool:

                sections.append(
                    "Suggested tool: "
                    f"{prompt_context.current_step.tool}",
                )

        if prompt_context.completed_steps:

            sections.append("Completed steps:")

            for step in prompt_context.completed_steps:

                sections.append(
                    f"- [{step.id}] {step.description} => "
                    f"{step.result[:200]}",
                )

        return [
            Message(
                role="system",
                content=(
                    "You are executing a multi-step plan. "
                    "Focus on the current step and use completed "
                    "step results when helpful.\n\n"
                    + "\n".join(sections)
                ),
            )
        ]

    def _format_rag_message(
        self,
        results: "list[ScoredDocument]",
    ) -> Message:

        sections: list[str] = []

        for index, scored in enumerate(results, start=1):

            source = scored.document.metadata.get(
                "source",
                scored.document.id,
            )

            sections.append(
                f"[{index}] (score={scored.score:.4f}, "
                f"source={source})\n"
                f"{scored.document.content}",
            )

        knowledge_text = "\n\n".join(sections)

        return Message(
            role="system",
            content=(
                "Use the following retrieved knowledge to "
                "answer the user's question. If the knowledge "
                "is insufficient, say so clearly.\n\n"
                f"{knowledge_text}",
            ),
        )

    def _embedding_provider_name(self) -> str:

        if self._retriever is None:

            return ""

        provider = getattr(
            self._retriever,
            "_embedding_provider",
            None,
        )

        if provider is None:

            return type(self._retriever).__name__

        return type(provider).__name__
