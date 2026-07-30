from __future__ import annotations

from app.agents.types import AgentContext
from app.llm.types import Message
from app.memory.manager import MemoryManager
from app.config import AgentConfig
from app.prompts.builder import PromptBuilder
from app.agents.executor.tracer import AgentTracer

from applications.software_team.agents.base.coordinator_context import (
    CoordinatorContext,
)
from applications.software_team.execution.verification_result import (
    VerificationFeedback,
)
from applications.software_team.deployment.deployment_result import DeploymentContext
from applications.software_team.management.management_result import ManagementContext
from applications.software_team.knowledge.knowledge_result import KnowledgeContext
from applications.software_team.operations.operation_history import OperationContext
from applications.software_team.git.git_context import GitContext
from applications.software_team.project.artifacts.artifact_manager import (
    ArtifactManager,
)
from applications.software_team.workflow.artifact_reader import ArtifactReader
from applications.platform.platform_result import PlatformContext
from applications.software_team.config.defaults import MAX_PROMPT_MESSAGE_CHARS
from applications.software_team.workflow.dependencies import (
    AgentDependencyRegistry,
)


class TeamPromptBuilder:
    """
    Software Team 专用 Prompt 构建器。

    组合 Framework PromptBuilder，自动注入：
    - User Requirement / Project / Workflow 阶段
    - Memory（通过 Framework MemoryManager）
    - 依赖 Artifact 内容
    - 验证失败反馈（Verification Result / Error Log / Previous Attempt）
    - Agent 角色与任务指令

    Agent 不手动拼接 Prompt，统一通过本类构建。
    """

    def __init__(
        self,
        dependency_registry: AgentDependencyRegistry | None = None,
        artifact_reader: ArtifactReader | None = None,
        config: AgentConfig | None = None,
        memory_manager: MemoryManager | None = None,
        tracer: AgentTracer | None = None,
    ):

        self._registry = (
            dependency_registry or AgentDependencyRegistry()
        )
        self._artifact_reader = (
            artifact_reader or ArtifactReader()
        )
        self._config = config or AgentConfig(
            enable_rag=False,
            enable_mcp=False,
            system_prompt_path=None,
        )
        self._memory_manager = (
            memory_manager or MemoryManager()
        )
        self._tracer = tracer

    def build(
        self,
        agent_name: str,
        context: CoordinatorContext,
        artifact_manager: ArtifactManager,
        *,
        task_instruction: str | None = None,
        verification_feedback: VerificationFeedback | None = None,
        git_context: GitContext | None = None,
        deployment_context: DeploymentContext | None = None,
        operation_context: OperationContext | None = None,
        management_context: ManagementContext | None = None,
        knowledge_context: KnowledgeContext | None = None,
        platform_context: PlatformContext | None = None,
    ) -> list[Message]:
        """
        为指定 Agent 构建完整 Prompt 消息列表。
        """

        dependencies = self._registry.get_dependencies(
            agent_name,
        )

        artifact_context = self._artifact_reader.resolve_dependencies(
            dependencies,
            artifact_manager,
            context.workspace_path,
        )

        feedback = (
            verification_feedback
            or VerificationFeedback.from_metadata(context.metadata)
        )

        instruction = (
            task_instruction
            or context.metadata.get("fix_instruction")
            or self._registry.get_task_instruction(agent_name)
        )

        shared_context = {
            **context.shared_context,
            "user_requirement": context.requirement,
            "project_name": context.project.name,
            "project_id": context.project.id,
            "workspace_path": context.workspace_path,
            "tech_stack": context.project.tech_stack,
            "task_instruction": instruction,
            **{
                f"dependency:{key}": value
                for key, value in artifact_context.items()
            },
        }

        if feedback is not None:

            shared_context.update(feedback.to_shared_context())

        git_ctx = git_context

        if git_ctx is None and context.metadata.get("git_context"):

            git_ctx = GitContext(
                workspace_path=context.workspace_path,
                is_initialized=True,
                current_branch=str(
                    context.shared_context.get(
                        "git_current_branch",
                        "",
                    )
                ),
                last_commit_sha=str(
                    context.shared_context.get(
                        "git_last_commit_sha",
                        "",
                    )
                ),
                last_commit_message=str(
                    context.shared_context.get(
                        "git_last_commit_message",
                        "",
                    )
                ),
            )

        if git_ctx is not None and git_ctx.is_initialized:

            shared_context.update(git_ctx.to_shared_context())

        deploy_ctx = deployment_context

        if deploy_ctx is None and context.metadata.get("deployment_context"):

            deploy_ctx = DeploymentContext(
                build_summary=str(
                    context.shared_context.get(
                        "deployment_build_result",
                        "",
                    )
                ),
                package_summary=str(
                    context.shared_context.get(
                        "deployment_package_result",
                        "",
                    )
                ),
                deploy_summary=str(
                    context.shared_context.get(
                        "deployment_deploy_result",
                        "",
                    )
                ),
                health_summary=str(
                    context.shared_context.get(
                        "deployment_health_result",
                        "",
                    )
                ),
                release_summary=str(
                    context.shared_context.get(
                        "deployment_release_result",
                        "",
                    )
                ),
                deploy_url=str(
                    context.shared_context.get("deployment_url", "")
                ),
                version=str(
                    context.shared_context.get("deployment_version", "")
                ),
            )

        if deploy_ctx is not None and (
            deploy_ctx.build_summary
            or deploy_ctx.health_summary
            or deploy_ctx.deploy_summary
        ):

            shared_context.update(deploy_ctx.to_shared_context())

        ops_ctx = operation_context

        if ops_ctx is None and context.metadata.get("operation_context"):

            ops_ctx = OperationContext(
                monitor_summary=str(
                    context.shared_context.get("operation_monitor", "")
                ),
                alert_summary=str(
                    context.shared_context.get("operation_alerts", "")
                ),
                incident_summary=str(
                    context.shared_context.get("operation_incident", "")
                ),
                diagnosis_summary=str(
                    context.shared_context.get("operation_diagnosis", "")
                ),
                maintenance_summary=str(
                    context.shared_context.get("operation_maintenance", "")
                ),
                deployment_history_summary=str(
                    context.shared_context.get(
                        "operation_deployment_history",
                        "",
                    )
                ),
            )

        if ops_ctx is not None and (
            ops_ctx.monitor_summary
            or ops_ctx.alert_summary
            or ops_ctx.incident_summary
            or ops_ctx.diagnosis_summary
        ):

            shared_context.update(ops_ctx.to_shared_context())

        mgmt_ctx = management_context

        if mgmt_ctx is None and context.metadata.get("management_context"):

            mgmt_ctx = ManagementContext(
                project_summary=str(
                    context.shared_context.get("mgmt_project_summary", "")
                ),
                current_milestone=str(
                    context.shared_context.get("mgmt_current_milestone", "")
                ),
                current_sprint=str(
                    context.shared_context.get("mgmt_current_sprint", "")
                ),
                task_status_summary=str(
                    context.shared_context.get("mgmt_task_status", "")
                ),
                risk_summary=str(
                    context.shared_context.get("mgmt_risk_summary", "")
                ),
                progress_summary=str(
                    context.shared_context.get("mgmt_progress_summary", "")
                ),
                workload_summary=str(
                    context.shared_context.get("mgmt_workload_summary", "")
                ),
            )

        if mgmt_ctx is not None and (
            mgmt_ctx.project_summary
            or mgmt_ctx.progress_summary
            or mgmt_ctx.task_status_summary
        ):

            shared_context.update(mgmt_ctx.to_shared_context())

        know_ctx = knowledge_context

        if know_ctx is None and context.metadata.get("knowledge_context"):

            know_ctx = KnowledgeContext(
                retrieval_summary=str(
                    context.shared_context.get("knowledge_retrieval", "")
                ),
                recommendation_summary=str(
                    context.shared_context.get("knowledge_recommendations", "")
                ),
                best_practices=str(
                    context.shared_context.get("knowledge_best_practices", "")
                ),
                lessons_learned=str(
                    context.shared_context.get("knowledge_lessons_learned", "")
                ),
                historical_solutions=str(
                    context.shared_context.get(
                        "knowledge_historical_solutions",
                        "",
                    )
                ),
                experience_summary=str(
                    context.shared_context.get("knowledge_experience", "")
                ),
            )

        if know_ctx is not None and (
            know_ctx.retrieval_summary
            or know_ctx.recommendation_summary
            or know_ctx.best_practices
        ):

            shared_context.update(know_ctx.to_shared_context())

        plat_ctx = platform_context

        if plat_ctx is None and context.metadata.get("platform_context"):

            plat_ctx = PlatformContext(
                organization_summary=str(
                    context.shared_context.get("platform_organization", "")
                ),
                workspace_summary=str(
                    context.shared_context.get("platform_workspace", "")
                ),
                permission_summary=str(
                    context.shared_context.get("platform_permission", "")
                ),
                project_summary=str(
                    context.shared_context.get("platform_project", "")
                ),
                team_summary=str(
                    context.shared_context.get("platform_team", "")
                ),
                model_summary=str(
                    context.shared_context.get("platform_model", "")
                ),
                governance_summary=str(
                    context.shared_context.get("platform_governance", "")
                ),
            )

        if plat_ctx is not None and (
            plat_ctx.organization_summary
            or plat_ctx.workspace_summary
            or plat_ctx.permission_summary
        ):

            shared_context.update(plat_ctx.to_shared_context())
            context.metadata["platform_context"] = True

        role_prompt = self._registry.get_role_prompt(agent_name)

        if feedback is not None:

            role_prompt = (
                f"{role_prompt}\n\n"
                "当前处于修复模式：上次验证失败，请根据 Verification Result "
                "与 Error Log 修复代码并重新提交。"
            )

        if ops_ctx is not None and context.metadata.get("operations_mode"):

            role_prompt = (
                f"{role_prompt}\n\n"
                "当前处于运维修复模式：请根据 Operation Context 中的 "
                "Alert、Incident 与 Diagnosis 定位并修复线上问题。"
            )

        agent_context = AgentContext(
            session_id=context.session_id,
            user_message=instruction,
            metadata={
                **context.metadata,
                "current_task": context.metadata.get(
                    "current_task",
                    instruction,
                ),
                "team_agent": agent_name,
                "dependency_keys": list(dependencies),
                "pipeline_step": agent_name,
                "project_id": context.project.id,
                "workspace_path": context.workspace_path,
                "verification_retry": bool(feedback),
            },
            agent_name=agent_name,
            agent_role=self._registry.get_role(agent_name),
            shared_context=shared_context,
        )

        builder = PromptBuilder(
            config=AgentConfig(
                max_iterations=self._config.max_iterations,
                enable_rag=self._config.enable_rag,
                enable_mcp=self._config.enable_mcp,
                system_prompt=role_prompt,
                system_prompt_path=None,
            ),
            memory_manager=self._memory_manager,
            tracer=self._tracer,
        )

        messages = builder.build(agent_context)
        messages = self._compact_messages(messages)

        if feedback is not None:

            messages.append(
                Message(
                    role="user",
                    content=self._build_verification_message(feedback),
                )
            )

        if git_ctx is not None and git_ctx.is_initialized:

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Git Context\n"
                        f"{git_ctx.to_prompt_block()}"
                    ),
                )
            )

        if deploy_ctx is not None and (
            deploy_ctx.build_summary
            or deploy_ctx.health_summary
            or deploy_ctx.deploy_summary
        ):

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Deployment Context\n"
                        f"{deploy_ctx.to_prompt_block()}\n\n"
                        "若部署失败，请根据 Build Result 与 Health Result "
                        "分析并修复相关问题。"
                    ),
                )
            )

        if ops_ctx is not None and (
            ops_ctx.monitor_summary
            or ops_ctx.alert_summary
            or ops_ctx.diagnosis_summary
        ):

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Operation Context\n"
                        f"{ops_ctx.to_prompt_block()}\n\n"
                        "请根据 Alert、Incident 与 Diagnosis 分析线上问题，"
                        "结合 Deployment History 定位根因并修复。"
                    ),
                )
            )

        if mgmt_ctx is not None and (
            mgmt_ctx.project_summary
            or mgmt_ctx.progress_summary
        ):

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Project Management Context\n"
                        f"{mgmt_ctx.to_prompt_block()}\n\n"
                        "请结合 Current Milestone、Task Status 与 Risk Summary "
                        "理解整个项目状态后再执行当前任务。"
                    ),
                )
            )

        if know_ctx is not None and (
            know_ctx.retrieval_summary
            or know_ctx.recommendation_summary
            or know_ctx.lessons_learned
        ):

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Knowledge Context\n"
                        f"{know_ctx.to_prompt_block()}\n\n"
                        "请结合 Best Practices、Lessons Learned 与 "
                        "Historical Solutions 复用已有经验，避免重复犯错。"
                    ),
                )
            )

        if plat_ctx is not None and (
            plat_ctx.organization_summary
            or plat_ctx.workspace_summary
            or plat_ctx.project_summary
        ):

            messages.append(
                Message(
                    role="user",
                    content=(
                        "## Enterprise Platform Context\n"
                        f"{plat_ctx.to_prompt_block()}\n\n"
                        "请遵守 Organization、Workspace 与 Permission 约束，"
                        "在 Project 与 Team 上下文中执行当前任务。"
                    ),
                )
            )

        return messages

    @classmethod
    def _compact_messages(
        cls,
        messages: list[Message],
    ) -> list[Message]:

        compact: list[Message] = []

        for message in messages:

            content = message.content

            if content and len(content) > MAX_PROMPT_MESSAGE_CHARS:

                content = (
                    f"{content[:MAX_PROMPT_MESSAGE_CHARS]}\n\n"
                    "...[prompt truncated "
                    f"{len(message.content or '') - MAX_PROMPT_MESSAGE_CHARS} chars]"
                )

            compact.append(
                Message(
                    role=message.role,
                    content=content,
                    tool_call_id=message.tool_call_id,
                    name=message.name,
                    tool_calls=message.tool_calls,
                )
            )

        return compact

    @staticmethod
    def _build_verification_message(
        feedback: VerificationFeedback,
    ) -> str:

        return (
            f"## 验证失败 — 第 {feedback.attempt} 次修复\n\n"
            f"### Verification Result\n{feedback.verification_summary}\n\n"
            f"### Execution Output\n{feedback.execution_summary}\n\n"
            f"### Error Log\n{feedback.error_log}\n\n"
            f"### Previous Attempt\n{feedback.previous_attempt_summary}\n\n"
            "请修复上述问题，使用 write_file 更新相关文件。"
        )
