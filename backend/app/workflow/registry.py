"""
Workflow 定义注册表。
"""

from __future__ import annotations

from app.workflow.graph import WorkflowGraph


class WorkflowRegistry:
    """
    按 workflow_id 注册可复用的 WorkflowGraph。
    """

    def __init__(self) -> None:

        self._graphs: dict[str, WorkflowGraph] = {}

    def register(
        self,
        graph: WorkflowGraph,
        *,
        overwrite: bool = False,
    ) -> None:

        if graph.id in self._graphs and not overwrite:

            raise ValueError(
                f"Workflow '{graph.id}' already registered"
            )

        graph.validate()
        self._graphs[graph.id] = graph

    def get(self, workflow_id: str) -> WorkflowGraph:

        if workflow_id not in self._graphs:

            raise KeyError(
                f"Workflow '{workflow_id}' not found. "
                f"Registered: {sorted(self._graphs)}"
            )

        return self._graphs[workflow_id]

    def list_ids(self) -> list[str]:

        return sorted(self._graphs.keys())

    def unregister(self, workflow_id: str) -> None:

        self._graphs.pop(workflow_id, None)


default_workflow_registry = WorkflowRegistry()
