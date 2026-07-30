"""
Agent Studio 服务层（Task 6.8）。
"""

from __future__ import annotations

from typing import Any

from app.memory.memory_manager import get_default_enterprise_memory_manager
from app.memory.types import MemoryKind
from app.observability.metrics import EnterpriseMetricsAggregator
from app.observability.serialization import event_to_dict
from app.observability.serialization import trace_to_dict
from app.observability.trace import default_trace_registry
from app.observability.trace import render_execution_timeline
from app.prompts.manager import get_default_prompt_manager
from app.prompts.repository import PROMPT_DEVELOPER
from app.prompts.version import PromptVersion
from app.studio.schemas import AgentStatusResponse
from app.studio.schemas import MemoryViewResponse
from app.studio.schemas import PromptViewResponse
from app.studio.schemas import ToolViewItem
from app.studio.schemas import ToolsViewResponse
from app.studio.schemas import TraceViewResponse
from app.studio.schemas import WorkflowViewResponse
from app.studio.store import StudioStore
from app.studio.store import default_studio_store
from app.tools.registry import ToolRegistry
from app.workflow.executor import WorkflowExecutor
from app.workflow.node import NodeType
from app.workflow.registry import default_workflow_registry


class AgentStudioService:
    def __init__(self, store: StudioStore | None = None) -> None:
        self._store = store or default_studio_store
        self._memory = get_default_enterprise_memory_manager()
        self._prompts = get_default_prompt_manager()

    @property
    def store(self) -> StudioStore:
        return self._store

    def bind_workflow_executor(self, executor: WorkflowExecutor) -> None:
        self._store.bind_executor(executor)

    def get_workflow(
        self,
        *,
        workflow_id: str | None = None,
        run_id: str | None = None,
    ) -> WorkflowViewResponse:
        graph = None

        if workflow_id:
            graph = default_workflow_registry.get(workflow_id)

        executor = self._store.workflow_executor
        run_result = None

        if run_id and executor is not None:
            run_result = executor.get_run(run_id)

            if run_result is not None and graph is None:
                graph = executor.get_run_graph(run_id)

        if graph is None and workflow_id:
            graph = default_workflow_registry.get(workflow_id)

        if graph is None:
            raise KeyError("workflow not found")

        nodes = [
            {
                "id": node.id,
                "type": node.type.value,
                "name": node.name,
                "config": dict(node.config),
            }
            for node in graph.nodes.values()
        ]
        edges = [
            {
                "from": edge.from_id,
                "to": edge.to_id,
                "condition": edge.condition,
            }
            for edge in graph.edges
        ]

        node_results: dict[str, Any] = {}

        if run_result is not None:
            node_results = {
                key: value.to_dict()
                for key, value in run_result.node_results.items()
            }

        return WorkflowViewResponse(
            workflow_id=graph.id,
            run_id=run_id,
            name=graph.name,
            description=graph.description,
            status=run_result.status.value if run_result else None,
            nodes=nodes,
            edges=edges,
            node_results=node_results,
            pending_node_id=run_result.pending_node_id if run_result else None,
        )

    def get_trace(
        self,
        *,
        trace_id: str | None = None,
        session_id: str | None = None,
    ) -> TraceViewResponse:
        trace = None

        if trace_id:
            trace = default_trace_registry.get(trace_id)

        if trace is None and session_id:
            traces = default_trace_registry.list_session(session_id)

            if traces:
                trace = traces[-1]

        if trace is None:
            raise KeyError("trace not found")

        timeline = render_execution_timeline(trace)
        metrics = EnterpriseMetricsAggregator.summarize_trace(trace)

        return TraceViewResponse(
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            duration_sec=trace.duration,
            timeline=timeline,
            events=[event_to_dict(event) for event in trace.events],
            metrics=metrics,
        )

    def get_prompt(
        self,
        *,
        prompt_id: str,
        version: str | None = None,
    ) -> PromptViewResponse:
        versions = self._prompts.list_versions(prompt_id)
        resolved = version or (versions[-1] if versions else "1.0.0")
        override = self._store.get_prompt_override(prompt_id, resolved)

        if override is not None:
            meta = self._prompts.get(prompt_id, version=resolved)

            return PromptViewResponse(
                prompt_id=prompt_id,
                version=resolved,
                role=meta.role,
                content=override,
                variables=list(meta.variables),
                overridden=True,
            )

        meta = self._prompts.get(prompt_id, version=resolved)
        content = self._prompts.repository.resolve_content(
            prompt_id,
            resolved,
        )

        return PromptViewResponse(
            prompt_id=prompt_id,
            version=resolved,
            role=meta.role,
            content=content,
            variables=list(meta.variables),
            overridden=False,
        )

    def update_prompt(
        self,
        *,
        prompt_id: str,
        version: str,
        content: str,
    ) -> PromptViewResponse:
        self._store.set_prompt_override(prompt_id, version, content)

        base = self._prompts.get(prompt_id, version=version)
        self._prompts.register(
            PromptVersion(
                prompt_id=prompt_id,
                version=version,
                content=content,
                role=base.role,
                parent_id=base.parent_id,
                parent_version=base.parent_version,
                description=f"studio override {base.description}".strip(),
            ),
            overwrite=True,
        )

        return self.get_prompt(prompt_id=prompt_id, version=version)

    def get_memory(
        self,
        *,
        session_id: str,
        project_id: str | None = None,
    ) -> MemoryViewResponse:
        pid = project_id or session_id
        merged = self._memory.load_merged(
            session_id,
            project_id=pid,
            knowledge_scope=pid,
        )

        conversation: list[dict[str, Any]] = []
        shared: list[dict[str, Any]] = []
        knowledge: list[dict[str, Any]] = []

        for record in merged.records:
            payload = {
                "role": record.role,
                "content": record.content,
                "metadata": dict(record.metadata),
            }
            kind = record.metadata.get("memory_kind")

            if kind == MemoryKind.SHARED.value:
                shared.append(payload)
            elif kind == MemoryKind.KNOWLEDGE.value:
                knowledge.append(payload)
            elif kind == MemoryKind.CONVERSATION.value:
                conversation.append(payload)

        return MemoryViewResponse(
            session_id=session_id,
            project_id=pid,
            conversation=conversation,
            project_memory=self._memory.load_project_snapshot(pid),
            shared=shared,
            knowledge=knowledge,
        )

    def list_tools(self) -> ToolsViewResponse:
        tools = [
            ToolViewItem(
                name=tool.name,
                description=tool.description,
                tool_schema=tool.schema,
            )
            for tool in ToolRegistry.get_all()
        ]

        return ToolsViewResponse(tools=tools)

    def get_agent_status(self, *, run_id: str) -> AgentStatusResponse:
        executor = self._store.workflow_executor

        if executor is None:
            raise RuntimeError("workflow executor not bound")

        run = executor.get_run(run_id)

        if run is None:
            raise KeyError(f"run not found: {run_id}")

        graph = executor.get_run_graph(run_id)

        if graph is None:
            raise KeyError(f"run not found: {run_id}")

        agents: dict[str, Any] = {}

        for node_id, node in graph.nodes.items():
            if node.type != NodeType.AGENT:
                continue

            result = run.node_results.get(node_id)
            agents[node_id] = {
                "agent_name": node.config.get("agent_name", ""),
                "status": result.status.value if result else "pending",
                "success": result.success if result else None,
                "output_preview": (result.output[:200] if result else ""),
            }

        return AgentStatusResponse(
            run_id=run_id,
            workflow_id=run.workflow_id,
            status=run.status.value,
            agents=agents,
            pending_node_id=run.pending_node_id,
        )

    def rerun_step(self, *, run_id: str, node_id: str) -> WorkflowViewResponse:
        executor = self._store.workflow_executor

        if executor is None:
            raise RuntimeError("workflow executor not bound")

        executor.rerun_step(run_id, node_id)
        run = executor.get_run(run_id)

        if run is None:
            raise KeyError("run not found after rerun")

        return self.get_workflow(workflow_id=run.workflow_id, run_id=run_id)


default_studio_service = AgentStudioService()

# 默认 Developer Prompt ID 便于 Studio UI
STUDIO_DEFAULT_PROMPT_ID = PROMPT_DEVELOPER
