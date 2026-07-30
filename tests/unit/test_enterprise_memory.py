"""Task 6.7 Enterprise Memory tests."""

from __future__ import annotations

from app.agents.software_team.developer_agent import DeveloperAgent
from app.agents.software_team.manager_agent import ProjectManagerAgent
from app.agents.software_team.task import SoftwareProject
from app.agents.software_team.task import SoftwareTeamTask
from app.agents.types import AgentContext
from app.memory.memory_manager import EnterpriseMemoryManager
from app.memory.types import MemoryKind


class _StubWorkflow:
    def create_project(self, requirement: str) -> SoftwareProject:
        task = SoftwareTeamTask(
            title="Implement API",
            description="Build REST login",
            agent="developer",
        )
        return SoftwareProject(
            name="demo",
            requirement=requirement,
            goal_summary="Deliver MVP",
            tasks=[task],
        )


def test_manager_and_developer_share_project_memory() -> None:
    memory = EnterpriseMemoryManager()
    session_id = "sess-mem"
    project_id = "proj-001"

    pm = ProjectManagerAgent(workflow=_StubWorkflow())
    ctx = AgentContext(
        session_id=session_id,
        user_message="Build login MVP",
        metadata={"project_id": project_id},
    )

    # Patch global memory used inside PM agent
    import app.memory.memory_manager as mm_mod

    original = mm_mod.get_default_enterprise_memory_manager
    mm_mod.get_default_enterprise_memory_manager = lambda: memory

    try:
        pm.execute(ctx)

        dev_ctx = AgentContext(
            session_id=session_id,
            user_message="start coding",
            metadata={"project_id": project_id, "workspace_dir": "/tmp/ws"},
            shared_context={},
        )

        dev = DeveloperAgent()
        dev.before_run(dev_ctx)

        task_text = DeveloperAgent._resolve_task_list(dev_ctx)
        assert "Implement API" in task_text or "developer" in task_text.lower()
    finally:
        mm_mod.get_default_enterprise_memory_manager = original


def test_memory_kinds_and_merge() -> None:
    memory = EnterpriseMemoryManager()
    session = "s1"
    project = "p1"

    memory.save_user_message(session, "hello")
    memory.write_project(project, "architecture", "microservices", agent_name="manager")
    memory.shared.publish(project, agent_name="manager", content="kickoff")
    memory.knowledge.append(project, content="OAuth2 standard", source="kb")

    merged = memory.load_merged(session, project_id=project, knowledge_scope=project)
    kinds = {record.metadata.get("memory_kind") for record in merged.records}

    assert MemoryKind.CONVERSATION.value in kinds
    assert MemoryKind.PROJECT.value in kinds
    assert MemoryKind.SHARED.value in kinds
    assert MemoryKind.KNOWLEDGE.value in kinds
