"""
WorkflowExecutor — DAG 调度、状态流转、错误恢复；经 AgentRuntime 调用 Agent。
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from typing import Protocol
from uuid import uuid4

from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.config import AgentConfig
from app.tools.types import ToolContext
from app.tools.types import ToolResult
from app.workflow.base import NodeExecutionResult
from app.workflow.base import NodeRunStatus
from app.workflow.base import OnFailureAction
from app.workflow.base import WorkflowExecutionContext
from app.workflow.base import WorkflowRunResult
from app.workflow.base import WorkflowRunStatus
from app.workflow.graph import WorkflowGraph
from app.workflow.human_node import HumanApprovalNode
from app.workflow.node import NodeType
from app.workflow.node import WorkflowNode


class ToolExecutor(Protocol):
    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult: ...


@dataclass
class _ActiveRun:
    graph: WorkflowGraph
    context: WorkflowExecutionContext
    completed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    branch_by_node: dict[str, str | None] = field(default_factory=dict)
    status: WorkflowRunStatus = WorkflowRunStatus.RUNNING
    pending_node_id: str | None = None
    pending_message: str = ""
    error: str = ""


class WorkflowExecutor:
    """
    执行 WorkflowGraph，不修改 AgentRuntime 实现。
    """

    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        *,
        config: AgentConfig | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> None:

        from app.agents.runtime import default_runtime

        self._runtime = runtime or default_runtime
        self._config = config
        self._tool_executor = tool_executor
        self._runs: dict[str, _ActiveRun] = {}

    def run(
        self,
        graph: WorkflowGraph,
        *,
        session_id: str,
        user_message: str = "",
        shared_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        run_id: str | None = None,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:

        graph.validate()

        rid = run_id or uuid4().hex[:12]

        context = WorkflowExecutionContext(
            session_id=session_id,
            run_id=rid,
            user_message=user_message,
            shared_context=dict(shared_context or {}),
            metadata=dict(metadata or {}),
        )

        context.shared_context.setdefault("user_message", user_message)

        active = _ActiveRun(
            graph=graph,
            context=context,
        )

        self._runs[rid] = active

        return self._execute_loop(
            active,
            agent_kwargs=agent_kwargs or {},
        )

    def resume(
        self,
        run_id: str,
        *,
        approval_payload: dict[str, Any] | None = None,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:

        active = self._runs.get(run_id)

        if active is None:

            raise ValueError(f"Unknown workflow run: {run_id}")

        if active.status != WorkflowRunStatus.WAITING_APPROVAL:

            raise ValueError(
                f"Run {run_id} is not waiting for approval "
                f"(status={active.status})"
            )

        pending = active.pending_node_id

        if pending and approval_payload is not None:
            node = active.graph.nodes.get(pending)
            prompt_key = "human_modified_prompt"

            if node is not None and node.type == NodeType.HUMAN_APPROVAL:
                human = HumanApprovalNode.from_workflow_node(node)
                prompt_key = human.context_prompt_key

            HumanApprovalNode.apply_payload(
                active.context,
                pending,
                approval_payload,
                context_prompt_key=prompt_key,
            )

        active.status = WorkflowRunStatus.RUNNING
        active.pending_node_id = None
        active.pending_message = ""

        return self._execute_loop(
            active,
            agent_kwargs=agent_kwargs or {},
        )

    def _execute_loop(
        self,
        active: _ActiveRun,
        *,
        agent_kwargs: dict[str, Any],
    ) -> WorkflowRunResult:

        graph = active.graph
        context = active.context

        while active.status == WorkflowRunStatus.RUNNING:

            self._auto_skip_unreachable(active)

            ready = self._ready_nodes(active)

            if not ready:

                if len(active.completed) + len(active.skipped) == len(
                    graph.nodes
                ):

                    active.status = WorkflowRunStatus.COMPLETED

                else:

                    active.status = WorkflowRunStatus.FAILED
                    active.error = active.error or "Deadlock: no ready nodes"

                break

            progressed = False

            for node_id in ready:

                node = graph.nodes[node_id]
                result = self._execute_node_with_recovery(
                    node,
                    context,
                    agent_kwargs=agent_kwargs,
                )

                context.set_node_output(node_id, result)

                if result.status == NodeRunStatus.WAITING_APPROVAL:

                    active.status = WorkflowRunStatus.WAITING_APPROVAL
                    active.pending_node_id = node_id
                    active.pending_message = result.output

                    return self._build_result(active)

                if result.status == NodeRunStatus.FAILED:

                    action = self._on_failure_action(node)

                    if action == OnFailureAction.SKIP:

                        active.skipped.add(node_id)
                        progressed = True
                        continue

                    if action == OnFailureAction.CONTINUE:

                        active.completed.add(node_id)
                        if node.type == NodeType.CONDITIONAL:

                            active.branch_by_node[node_id] = (
                                result.data.get("branch")
                            )

                        progressed = True
                        continue

                    active.status = WorkflowRunStatus.FAILED
                    active.error = result.error or result.output

                    return self._build_result(active)

                active.completed.add(node_id)

                if node.type == NodeType.CONDITIONAL:

                    active.branch_by_node[node_id] = result.data.get(
                        "branch"
                    )

                progressed = True

            if not progressed:

                active.status = WorkflowRunStatus.FAILED
                active.error = "No progress in scheduling wave"

                break

        if active.status == WorkflowRunStatus.RUNNING:

            active.status = WorkflowRunStatus.COMPLETED

        return self._build_result(active)

    def _ready_nodes(self, active: _ActiveRun) -> list[str]:

        graph = active.graph
        ready: list[str] = []

        for node_id in graph.nodes:

            if node_id in active.completed or node_id in active.skipped:

                continue

            if node_id == active.pending_node_id:

                ready.append(node_id)
                continue

            required = self._required_predecessors(active, node_id)

            if not required:

                if not self._predecessors(graph, node_id):

                    ready.append(node_id)

                continue

            if required <= active.completed | active.skipped:

                ready.append(node_id)

        return sorted(set(ready))

    def _required_predecessors(
        self,
        active: _ActiveRun,
        node_id: str,
    ) -> set[str]:

        graph = active.graph
        required: set[str] = set()

        for edge in graph.edges:

            if edge.to_id != node_id:

                continue

            if edge.condition is None:

                required.add(edge.from_id)
                continue

            branch = active.branch_by_node.get(edge.from_id)

            if edge.matches_branch(branch):

                required.add(edge.from_id)

        return required

    def _auto_skip_unreachable(self, active: _ActiveRun) -> None:

        graph = active.graph

        for node_id in graph.nodes:

            if node_id in active.completed or node_id in active.skipped:

                continue

            if not self._predecessors(graph, node_id):

                continue

            if self._required_predecessors(active, node_id):

                continue

            preds = self._predecessors(graph, node_id)

            if all(
                pred in active.completed or pred in active.skipped
                for pred in preds
            ):

                active.skipped.add(node_id)

    def _predecessors(
        self,
        graph: WorkflowGraph,
        node_id: str,
    ) -> list[str]:

        preds: list[str] = []

        for edge in graph.edges:

            if edge.to_id == node_id:

                preds.append(edge.from_id)

        return preds

    def _execute_node_with_recovery(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
        *,
        agent_kwargs: dict[str, Any],
    ) -> NodeExecutionResult:

        attempts = 0
        max_attempts = max(1, node.max_retries + 1)

        last: NodeExecutionResult | None = None

        while attempts < max_attempts:

            attempts += 1
            last = self._execute_node(
                node,
                context,
                agent_kwargs=agent_kwargs,
            )
            last.attempts = attempts

            if last.status != NodeRunStatus.FAILED:

                return last

            if attempts >= max_attempts:

                return last

        return last or NodeExecutionResult(
            node_id=node.id,
            status=NodeRunStatus.FAILED,
            success=False,
            error="execution failed",
        )

    def _execute_node(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
        *,
        agent_kwargs: dict[str, Any],
    ) -> NodeExecutionResult:

        if node.type == NodeType.AGENT:

            return self._run_agent_node(
                node,
                context,
                agent_kwargs=agent_kwargs,
            )

        if node.type == NodeType.TOOL:

            return self._run_tool_node(node, context)

        if node.type == NodeType.HUMAN_APPROVAL:

            return self._run_human_approval_node(node, context)

        if node.type == NodeType.CONDITIONAL:

            return self._run_conditional_node(node, context)

        return NodeExecutionResult(
            node_id=node.id,
            status=NodeRunStatus.FAILED,
            success=False,
            error=f"Unknown node type: {node.type}",
        )

    def _run_agent_node(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
        *,
        agent_kwargs: dict[str, Any],
    ) -> NodeExecutionResult:

        agent_name = str(node.config.get("agent_name", "")).strip()

        if not agent_name:

            return NodeExecutionResult(
                node_id=node.id,
                status=NodeRunStatus.FAILED,
                success=False,
                error="agent_name is required",
            )

        template = str(
            node.config.get(
                "message_template",
                "{user_message}",
            )
        )

        message = _render_template(
            template,
            context.shared_context,
            user_message=context.user_message,
        )

        meta = dict(context.metadata)
        meta.update(node.config.get("metadata") or {})
        meta["workflow_node_id"] = node.id
        meta["workflow_run_id"] = context.run_id

        task = AgentTask(
            session_id=context.session_id,
            user_message=message,
            agent_name=agent_name,
            shared_context=dict(context.shared_context),
            metadata=meta,
        )

        try:

            result = self._runtime.run(
                task,
                config=self._config,
                **agent_kwargs,
            )

        except Exception as error:

            return NodeExecutionResult(
                node_id=node.id,
                status=NodeRunStatus.FAILED,
                success=False,
                error=str(error),
            )

        context.shared_context["last_agent_success"] = result.success
        context.shared_context["last_agent_output"] = result.content

        status = (
            NodeRunStatus.COMPLETED
            if result.success
            else NodeRunStatus.FAILED
        )

        return NodeExecutionResult(
            node_id=node.id,
            status=status,
            success=result.success,
            output=result.content or "",
            data={"model": result.model},
            error="" if result.success else (result.content or "failed"),
        )

    def _run_tool_node(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
    ) -> NodeExecutionResult:

        if self._tool_executor is None:

            return NodeExecutionResult(
                node_id=node.id,
                status=NodeRunStatus.FAILED,
                success=False,
                error="Tool executor not configured",
            )

        tool_name = str(node.config.get("tool_name", ""))
        arguments = dict(node.config.get("arguments") or {})

        resolved = {
            key: _resolve_value(value, context.shared_context)
            for key, value in arguments.items()
        }

        try:

            tool_result = self._tool_executor.execute(
                tool_name,
                resolved,
            )

        except Exception as error:

            return NodeExecutionResult(
                node_id=node.id,
                status=NodeRunStatus.FAILED,
                success=False,
                error=str(error),
            )

        status = (
            NodeRunStatus.COMPLETED
            if tool_result.success
            else NodeRunStatus.FAILED
        )

        return NodeExecutionResult(
            node_id=node.id,
            status=status,
            success=tool_result.success,
            output=tool_result.content,
            error="" if tool_result.success else tool_result.content,
        )

    def _run_human_approval_node(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
    ) -> NodeExecutionResult:

        human = HumanApprovalNode.from_workflow_node(node)
        return human.evaluate(context)

    def _run_conditional_node(
        self,
        node: WorkflowNode,
        context: WorkflowExecutionContext,
    ) -> NodeExecutionResult:

        source_key = str(node.config.get("source_key", ""))
        expected = node.config.get("equals", True)

        actual = _get_path(context.shared_context, source_key)

        branch = "true" if actual == expected else "false"

        context.shared_context["__branch__"] = branch

        return NodeExecutionResult(
            node_id=node.id,
            status=NodeRunStatus.COMPLETED,
            success=True,
            output=f"branch={branch}",
            data={"branch": branch, "actual": actual},
        )

    @staticmethod
    def _on_failure_action(node: WorkflowNode) -> OnFailureAction:

        raw = str(node.on_failure or "fail").lower()

        if raw == "skip":

            return OnFailureAction.SKIP

        if raw == "continue":

            return OnFailureAction.CONTINUE

        if raw == "retry":

            return OnFailureAction.RETRY

        return OnFailureAction.FAIL

    def get_run(self, run_id: str) -> WorkflowRunResult | None:
        active = self._runs.get(run_id)

        if active is None:
            return None

        return self._build_result(active)

    def get_run_graph(self, run_id: str) -> WorkflowGraph | None:
        active = self._runs.get(run_id)

        if active is None:
            return None

        return active.graph

    def rerun_step(
        self,
        run_id: str,
        node_id: str,
        *,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        active = self._runs.get(run_id)

        if active is None:
            raise ValueError(f"Unknown workflow run: {run_id}")

        if node_id not in active.graph.nodes:
            raise ValueError(f"Unknown node: {node_id}")

        downstream = self._collect_downstream(active.graph, node_id)
        reset_nodes = {node_id} | downstream

        active.completed -= reset_nodes
        active.skipped -= reset_nodes

        for nid in reset_nodes:
            active.context.node_results.pop(nid, None)

        active.branch_by_node.pop(node_id, None)
        active.status = WorkflowRunStatus.RUNNING
        active.pending_node_id = None
        active.pending_message = ""
        active.error = ""

        return self._execute_loop(
            active,
            agent_kwargs=agent_kwargs or {},
        )

    @staticmethod
    def _collect_downstream(
        graph: WorkflowGraph,
        node_id: str,
    ) -> set[str]:
        visited: set[str] = set()
        queue = deque([node_id])

        while queue:
            current = queue.popleft()

            for edge in graph.edges:
                if edge.from_id != current:
                    continue

                if edge.to_id in visited:
                    continue

                visited.add(edge.to_id)
                queue.append(edge.to_id)

        visited.discard(node_id)
        return visited

    def _build_result(self, active: _ActiveRun) -> WorkflowRunResult:

        return WorkflowRunResult(
            workflow_id=active.graph.id,
            run_id=active.context.run_id,
            status=active.status,
            shared_context=dict(active.context.shared_context),
            node_results=dict(active.context.node_results),
            error=active.error,
            pending_node_id=active.pending_node_id,
            pending_message=active.pending_message,
        )


def _render_template(
    template: str,
    shared: dict[str, Any],
    *,
    user_message: str,
) -> str:

    values = dict(shared)
    values.setdefault("user_message", user_message)

    def replacer(match: re.Match[str]) -> str:

        key = match.group(1)
        value = _get_path(values, key)

        return str(value) if value is not None else ""

    return re.sub(r"\{([^}]+)\}", replacer, template)


def _get_path(data: dict[str, Any], key: str) -> Any:

    if not key:

        return None

    if key in data:

        return data[key]

    parts = key.split(".")
    current: Any = data

    for part in parts:

        if not isinstance(current, dict):

            return None

        current = current.get(part)

    return current


def _resolve_value(value: Any, shared: dict[str, Any]) -> Any:

    if isinstance(value, str) and value.startswith("{") and value.endswith(
        "}"
    ):

        return _get_path(shared, value[1:-1])

    return value
