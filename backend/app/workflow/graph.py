"""
WorkflowGraph — 可配置 DAG。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field

from app.workflow.edge import WorkflowEdge
from app.workflow.node import WorkflowNode


@dataclass
class WorkflowGraph:
    id: str
    name: str = ""
    description: str = ""
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: list[WorkflowEdge] = field(default_factory=list)
    entry_node_id: str | None = None

    def add_node(self, node: WorkflowNode) -> None:

        if node.id in self.nodes:

            raise ValueError(f"Duplicate node id: {node.id}")

        self.nodes[node.id] = node

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        *,
        condition: str | None = None,
    ) -> None:

        if from_id not in self.nodes or to_id not in self.nodes:

            raise ValueError(
                f"Edge references unknown node: {from_id} -> {to_id}"
            )

        self.edges.append(
            WorkflowEdge(
                from_id=from_id,
                to_id=to_id,
                condition=condition,
            )
        )

    def validate(self) -> None:

        if not self.nodes:

            raise ValueError("Workflow graph has no nodes")

        self._assert_acyclic()

        entry = self._entry_nodes()

        if not entry:

            raise ValueError("No entry node (check for cycle or orphan)")

        if self.entry_node_id and self.entry_node_id not in self.nodes:

            raise ValueError(f"Unknown entry_node_id: {self.entry_node_id}")

    def topological_order(
        self,
        *,
        branch_filter: dict[str, str | None] | None = None,
    ) -> list[str]:

        """
        返回拓扑序。branch_filter: from_id -> 仅沿该 condition 的后继扩展（用于条件边）。
        默认忽略 condition，按全 DAG 拓扑排序。
        """

        self.validate()

        incoming = {node_id: 0 for node_id in self.nodes}

        outgoing: dict[str, list[WorkflowEdge]] = {
            node_id: [] for node_id in self.nodes
        }

        for edge in self.edges:

            if branch_filter is not None:

                required = branch_filter.get(edge.from_id)

                if required is not None and not edge.matches_branch(
                    required
                ):

                    continue

            incoming[edge.to_id] += 1
            outgoing[edge.from_id].append(edge)

        starts = self._entry_nodes()

        if self.entry_node_id:

            starts = [self.entry_node_id]

        queue = deque(
            sorted(
                node_id
                for node_id in starts
                if incoming[node_id] == 0
            )
        )

        order: list[str] = []

        while queue:

            current = queue.popleft()
            order.append(current)

            for edge in outgoing[current]:

                incoming[edge.to_id] -= 1

                if incoming[edge.to_id] == 0:

                    queue.append(edge.to_id)

        if len(order) != len(self.nodes):

            raise ValueError("Graph has cycle or unreachable nodes")

        return order

    def successors(
        self,
        node_id: str,
        branch: str | None = None,
    ) -> list[str]:

        result: list[str] = []

        for edge in self.edges:

            if edge.from_id != node_id:

                continue

            if not edge.matches_branch(branch):

                continue

            result.append(edge.to_id)

        return result

    def _entry_nodes(self) -> list[str]:

        has_incoming = {edge.to_id for edge in self.edges}

        entries = [
            node_id
            for node_id in self.nodes
            if node_id not in has_incoming
        ]

        return entries

    def _assert_acyclic(self) -> None:

        incoming = {node_id: 0 for node_id in self.nodes}

        for edge in self.edges:

            incoming[edge.to_id] += 1

        queue = deque(
            node_id
            for node_id, count in incoming.items()
            if count == 0
        )

        visited = 0

        outgoing: dict[str, list[str]] = {
            node_id: [] for node_id in self.nodes
        }

        for edge in self.edges:

            outgoing[edge.from_id].append(edge.to_id)

        while queue:

            current = queue.popleft()
            visited += 1

            for nxt in outgoing[current]:

                incoming[nxt] -= 1

                if incoming[nxt] == 0:

                    queue.append(nxt)

        if visited != len(self.nodes):

            raise ValueError("Workflow graph contains a cycle")
