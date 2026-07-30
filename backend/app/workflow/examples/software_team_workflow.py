"""
示例：软件团队线性 + 条件 + 人工审批 Workflow。

注册 ID: software_team_v1
"""

from __future__ import annotations

from app.workflow.graph import WorkflowGraph
from app.workflow.node import WorkflowNode
from app.workflow.registry import default_workflow_registry


def build_software_team_workflow() -> WorkflowGraph:

    graph = WorkflowGraph(
        id="software_team_v1",
        name="AI Software Team",
        description=(
            "Product → Architecture → Developer → "
            "Conditional(review) → Human Approval → Tester"
        ),
        entry_node_id="product",
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="product",
            agent_name="product",
            name="Product PRD",
            message_template="{user_message}",
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="architecture",
            agent_name="architecture",
            name="Architecture",
            message_template="{node:product:output}",
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="developer",
            agent_name="developer",
            name="Developer",
            message_template="Implement MVP per architecture",
            extra_metadata={"workspace_dir": "{metadata.workspace_dir}"},
        )
    )

    graph.add_node(
        WorkflowNode.conditional(
            node_id="check_dev",
            source_key="last_agent_success",
            equals=True,
            name="Developer succeeded?",
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="reviewer",
            agent_name="reviewer",
            name="Reviewer",
            message_template="Review changes",
            on_failure="skip",
        )
    )

    graph.add_node(
        WorkflowNode.human_approval(
            node_id="approve_release",
            prompt="Approve release to testing?",
        )
    )

    graph.add_node(
        WorkflowNode.agent(
            node_id="tester",
            agent_name="tester",
            name="Tester",
            message_template="Run pytest suite",
        )
    )

    graph.add_node(
        WorkflowNode.tool(
            node_id="notify",
            tool_name="echo",
            arguments={"message": "Workflow completed"},
            name="Notify",
        )
    )

    graph.add_edge("product", "architecture")
    graph.add_edge("architecture", "developer")
    graph.add_edge("developer", "check_dev")
    graph.add_edge("check_dev", "reviewer", condition="true")
    graph.add_edge("check_dev", "notify", condition="false")
    graph.add_edge("reviewer", "approve_release")
    graph.add_edge("approve_release", "tester")
    graph.add_edge("tester", "notify")

    return graph


def register_default_workflows() -> None:

    default_workflow_registry.register(
        build_software_team_workflow(),
        overwrite=True,
    )
