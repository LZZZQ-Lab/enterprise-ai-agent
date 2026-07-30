"""
Team Workflow：Manager → Developer → Human Approval → Reviewer → Tester

注册 ID: team_with_human_approval_v1
"""

from __future__ import annotations

from app.workflow.graph import WorkflowGraph
from app.workflow.human_node import HumanApprovalNode
from app.workflow.node import WorkflowNode


def build_team_human_approval_workflow() -> WorkflowGraph:
    graph = WorkflowGraph(
        id="team_with_human_approval_v1",
        name="Team with Human Gate",
        description=(
            "Manager → Developer → Human Approval → Reviewer → Tester"
        ),
        entry_node_id="manager",
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="manager",
            agent_name="manager",
            name="Manager",
            message_template="{user_message}",
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="developer",
            agent_name="developer",
            name="Developer",
            message_template=(
                "Implement based on manager plan:\n{node:manager:output}"
            ),
        )
    )

    human = HumanApprovalNode(
        node_id="human_gate",
        prompt=(
            "Review developer output before code review. "
            "Approve, reject, or provide modified instructions."
        ),
        name="Human Approval Gate",
    )
    graph.add_node(human.to_workflow_node())

    graph.add_node(
        WorkflowNode.agent(
            node_id="reviewer",
            agent_name="reviewer",
            name="Reviewer",
            message_template=(
                "{human_modified_prompt}"
                "\n\nDeveloper output:\n{node:developer:output}"
            ),
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="tester",
            agent_name="tester",
            name="Tester",
            message_template="Run tests for:\n{node:developer:output}",
        )
    )

    graph.add_edge("manager", "developer")
    graph.add_edge("developer", "human_gate")
    graph.add_edge("human_gate", "reviewer")
    graph.add_edge("reviewer", "tester")

    return graph


def register_team_human_approval_workflow() -> None:
    from app.workflow.registry import default_workflow_registry

    default_workflow_registry.register(
        build_team_human_approval_workflow(),
        overwrite=True,
    )
