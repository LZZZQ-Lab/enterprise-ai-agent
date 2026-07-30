"""
Task 6.7 Enterprise Memory Demo。

演示 Manager 写入 Project Memory → Developer 读取。

运行:
    cd backend
    python -m applications.memory.run_memory_demo
"""

from __future__ import annotations

from app.agents.software_team.developer_agent import DeveloperAgent
from app.agents.software_team.manager_agent import ProjectManagerAgent
from app.agents.software_team.task import SoftwareProject
from app.agents.software_team.task import SoftwareTeamTask
from app.agents.types import AgentContext
from app.memory.memory_manager import EnterpriseMemoryManager


class DemoWorkflow:
    def create_project(self, requirement: str) -> SoftwareProject:
        return SoftwareProject(
            name="Memory Demo",
            requirement=requirement,
            goal_summary="Shared memory demo",
            tasks=[
                SoftwareTeamTask(
                    title="Auth module",
                    description="JWT login endpoint",
                    agent="developer",
                ),
            ],
        )


def main() -> None:
    print("Enterprise Memory Demo (Task 6.7)\n")

    memory = EnterpriseMemoryManager()

    import app.memory.memory_manager as mm

    mm.get_default_enterprise_memory_manager = lambda: memory

    session = "demo-session"
    project_id = "demo-project"

    pm = ProjectManagerAgent(workflow=DemoWorkflow())
    pm_ctx = AgentContext(
        session_id=session,
        user_message="Enterprise SSO integration",
        metadata={"project_id": project_id},
    )
    pm.execute(pm_ctx)

    print("Project Memory after Manager:")
    for key, value in memory.load_project_snapshot(project_id).items():
        print(f"  {key}: {value[:80]}...")

    dev_ctx = AgentContext(
        session_id=session,
        user_message="implement",
        metadata={"project_id": project_id, "workspace_dir": "/tmp/demo"},
        shared_context={},
    )
    dev = DeveloperAgent()
    dev.before_run(dev_ctx)
    tasks = DeveloperAgent._resolve_task_list(dev_ctx)

    print("\nDeveloper sees task list from Project Memory:")
    print(tasks)

    merged = memory.load_merged(session, project_id=project_id)
    print(f"\nMerged memory records: {len(merged.records)}")

    print("\nDemo finished.")


if __name__ == "__main__":
    main()
