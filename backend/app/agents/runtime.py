from __future__ import annotations

import threading
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.agents.factory import AgentFactory
from app.agents.registry import AgentRegistry
from app.agents.registry import registry as default_registry
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig
from app.memory.types import MemoryRecord


@dataclass
class AgentTask:
    """
    Agent Runtime 任务描述。
    """

    session_id: str
    user_message: str
    agent_name: str = ""
    history: list[MemoryRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_role: str = ""
    shared_context: dict[str, Any] = field(default_factory=dict)


class AgentRuntime:
    """
    企业级 Agent 运行框架。

    职责：
    - 接收任务（AgentTask）并提交 Agent Scheduler
    - 由 Scheduler Worker 调用 execute_task / run_context 执行 Agent
    - 返回 AgentResult
    """

    DEFAULT_AGENT = "chat"

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        factory: type[AgentFactory] | None = None,
        default_agent: str | None = None,
        default_config: AgentConfig | None = None,
        scheduler: Any | None = None,
    ) -> None:

        self._registry = registry or default_registry
        self._factory = factory or AgentFactory
        self._default_agent = default_agent or self.DEFAULT_AGENT
        self._default_config = default_config
        self._scheduler = scheduler
        self._scheduler_lock = threading.Lock()

    @property
    def registry(self) -> AgentRegistry:

        return self._registry

    @property
    def default_agent(self) -> str:

        return self._default_agent

    def _ensure_scheduler(self) -> Any:
        """
        懒加载默认 AgentScheduler，并绑定 execute_task。
        """

        if self._scheduler is not None:
            return self._scheduler

        with self._scheduler_lock:
            if self._scheduler is not None:
                return self._scheduler

            from app.scheduler.scheduler import AgentScheduler

            self._scheduler = AgentScheduler(
                worker_count=2,
                auto_start=True,
            )
            self._scheduler.set_executor(self.execute_task)

            return self._scheduler

    def create_context(
        self,
        task: AgentTask,
    ) -> AgentContext:
        """
        将 AgentTask 转换为 AgentContext。
        """

        agent_name = task.agent_name or self._default_agent

        return AgentContext(
            session_id=task.session_id,
            user_message=task.user_message,
            history=list(task.history),
            metadata=dict(task.metadata),
            agent_name=agent_name,
            agent_role=task.agent_role,
            shared_context=dict(task.shared_context),
        )

    def resolve_agent_name(
        self,
        agent_name: str | None = None,
        context: AgentContext | None = None,
    ) -> str:
        """
        解析最终使用的 Agent 名称。
        """

        if agent_name:

            return agent_name

        if context is not None and context.agent_name:

            return context.agent_name

        return self._default_agent

    def resolve_config(
        self,
        config: AgentConfig | None = None,
    ) -> AgentConfig:
        """
        解析最终 Agent 配置，优先使用传入值，否则读取 Settings。
        """

        if config is not None:

            return config

        if self._default_config is not None:

            return self._default_config

        return AgentConfig.from_env()

    def run(
        self,
        task: AgentTask,
        *,
        config: AgentConfig | None = None,
        **agent_kwargs: Any,
    ) -> AgentResult:
        """
        提交任务至 Agent Scheduler，阻塞等待结果。
        """

        scheduler = self._ensure_scheduler()
        return scheduler.submit_and_wait(
            task,
            config=config,
            agent_kwargs=agent_kwargs,
        )

    def execute_task(
        self,
        task: AgentTask,
        config: AgentConfig | None = None,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> AgentResult:
        """
        由 Scheduler Worker 调用，直接执行 Agent（不经过队列）。
        """

        context = self.create_context(task)
        agent_name = self.resolve_agent_name(task.agent_name, context)

        return self.run_context(
            context,
            agent_name=agent_name,
            config=self.resolve_config(config),
            **(agent_kwargs or {}),
        )

    def run_context(
        self,
        context: AgentContext,
        *,
        agent_name: str | None = None,
        config: AgentConfig | None = None,
        **agent_kwargs: Any,
    ) -> AgentResult:
        """
        使用已有 AgentContext 执行 Agent。
        """

        resolved_name = self.resolve_agent_name(agent_name, context)

        self._registry.get(resolved_name)

        agent = self._factory.create(
            resolved_name,
            config=self.resolve_config(config),
            registry=self._registry,
            **agent_kwargs,
        )

        from app.observability.collector import TraceCollector
        from app.observability.trace import agent_execution_trace

        external = context.metadata.get("_trace_collector")

        if isinstance(external, TraceCollector):
            result = agent.run(context)
            return result

        with agent_execution_trace(
            session_id=context.session_id,
            agent_name=resolved_name,
            prompt=context.user_message,
            metadata={
                "agent_role": context.agent_role,
                **dict(context.metadata),
            },
        ) as trace_session:
            context.metadata["_trace_collector"] = trace_session.collector
            try:
                result = agent.run(context)
            finally:
                context.metadata.pop("_trace_collector", None)

            trace_session.finish(
                response=result.content or "",
                success=result.success,
            )

            return result


default_runtime = AgentRuntime()
