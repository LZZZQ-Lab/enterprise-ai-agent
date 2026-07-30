from typing import TYPE_CHECKING

from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.multi_agent.message_bus import MessageBus
from app.multi_agent.registry import AgentRegistry
from app.multi_agent.router import AgentRouter
from app.multi_agent.router import RuleBasedRouter
from app.multi_agent.shared_memory import SharedMemory
from app.multi_agent.task import Task
from app.multi_agent.task import TaskStatus
from app.config import AgentConfig

if TYPE_CHECKING:
    from app.agents.executor.tracer import AgentTracer


class Coordinator:
    """
    Multi-Agent 协调器。

    接收用户任务 → Router 选 Agent → 分配子 Task → 收集结果 → 返回最终答案。
    enable_multi_agent=False 时退化为单 Agent 执行。
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: AgentConfig | None = None,
        router: AgentRouter | None = None,
        message_bus: MessageBus | None = None,
        shared_memory: SharedMemory | None = None,
        tracer: "AgentTracer | None" = None,
    ):

        self._registry = registry
        self._config = config or AgentConfig.from_env()
        self._router = router or RuleBasedRouter()
        self._message_bus = message_bus or MessageBus()
        self._shared_memory = shared_memory or SharedMemory()
        self._tracer = tracer

    @property
    def registry(self) -> AgentRegistry:

        return self._registry

    @property
    def message_bus(self) -> MessageBus:

        return self._message_bus

    @property
    def shared_memory(self) -> SharedMemory:

        return self._shared_memory

    def run(
        self,
        session_id: str,
        user_input: str,
        metadata: dict | None = None,
    ) -> AgentResult:

        if not self._config.enable_multi_agent:

            return self._run_single_agent(
                session_id,
                user_input,
                metadata,
            )

        root_task = Task(
            goal=user_input,
            input=user_input,
            metadata=metadata or {},
        )

        if self._tracer is not None:

            self._tracer.on_coordinator_start(
                user_input,
                len(self._registry),
            )

        subtasks = self._decompose(root_task)

        root_task.subtasks = subtasks

        self._shared_memory.set_workflow_state(
            {
                "goal": user_input,
                "status": "running",
                "total_tasks": len(subtasks),
            }
        )

        completed_results: list[tuple[str, str, AgentResult]] = []

        for subtask in subtasks[: self._config.max_agents]:

            result = self._execute_subtask(
                session_id,
                subtask,
                root_task,
            )

            completed_results.append(
                (
                    subtask.assigned_agent,
                    subtask.goal,
                    result,
                )
            )

        final_result = self._synthesize(
            session_id,
            root_task,
            completed_results,
        )

        self._shared_memory.update_workflow_state(
            status="completed",
        )

        if self._tracer is not None:

            self._tracer.on_coordinator_complete(
                user_input,
                final_result.success,
            )

        return final_result

    def _run_single_agent(
        self,
        session_id: str,
        user_input: str,
        metadata: dict | None,
    ) -> AgentResult:

        agent = self._router.route(
            user_input,
            self._registry,
            metadata,
        )

        if agent is None:

            return AgentResult(
                success=False,
                model="",
                content="No agent available to handle the request.",
            )

        context = AgentContext(
            session_id=session_id,
            user_message=user_input,
            metadata=dict(metadata or {}),
        )

        return agent.run(context)

    def _execute_subtask(
        self,
        session_id: str,
        subtask: Task,
        root_task: Task,
    ) -> AgentResult:

        subtask.status = TaskStatus.RUNNING

        agent = self._router.route(
            subtask.input,
            self._registry,
            subtask.metadata,
        )

        if agent is None:

            subtask.status = TaskStatus.FAILED
            subtask.output = "No agent found."

            return AgentResult(
                success=False,
                model="",
                content=subtask.output,
            )

        subtask.assigned_agent = agent.name

        if self._tracer is not None:

            self._tracer.on_agent_routing(
                task_input=subtask.input,
                selected_agent=agent.name,
                goal=root_task.goal,
            )

        shared_context = self._shared_memory.get_context_snapshot()

        profile = getattr(agent, "profile", None)

        context = AgentContext(
            session_id=session_id,
            user_message=subtask.input,
            metadata={
                **subtask.metadata,
                "current_task": subtask.goal,
                "root_goal": root_task.goal,
            },
            agent_name=agent.name,
            agent_role=profile.role if profile is not None else "",
            shared_context=shared_context,
        )

        if self._config.communication_mode == "bus":

            request = self._message_bus.send_request(
                sender="coordinator",
                receiver=agent.name,
                payload={
                    "task_id": subtask.id,
                    "goal": subtask.goal,
                    "input": subtask.input,
                },
                correlation_id=subtask.id,
            )

            if self._tracer is not None:

                self._tracer.on_message_bus(
                    sender=request.sender,
                    receiver=request.receiver,
                    message_type=request.message_type.value,
                    payload_preview=str(request.payload),
                )

        result = agent.run(context)

        subtask.output = result.content or ""
        subtask.status = (
            TaskStatus.COMPLETED
            if result.success
            else TaskStatus.FAILED
        )

        self._shared_memory.set(
            f"task:{subtask.id}",
            subtask.output,
            agent_name=agent.name,
            task_id=subtask.id,
        )

        self._shared_memory.set(
            f"agent:{agent.name}:last_result",
            subtask.output,
            agent_name=agent.name,
            task_id=subtask.id,
        )

        if self._config.communication_mode == "bus":

            response = self._message_bus.send_response(
                sender=agent.name,
                receiver="coordinator",
                payload={
                    "task_id": subtask.id,
                    "output": subtask.output,
                },
                correlation_id=subtask.id,
                success=result.success,
            )

            if self._tracer is not None:

                self._tracer.on_message_bus(
                    sender=response.sender,
                    receiver=response.receiver,
                    message_type=response.message_type.value,
                    payload_preview=str(response.payload),
                )

        if self._tracer is not None:

            self._tracer.on_coordinator_dispatch(
                agent_name=agent.name,
                task_id=subtask.id,
                success=result.success,
            )

        return result

    def _decompose(
        self,
        root_task: Task,
    ) -> list[Task]:

        goal = root_task.input.lower()

        if any(
            keyword in goal
            for keyword in (
                "旅行",
                "旅游",
                "travel",
                "东京",
                "tokyo",
            )
        ):

            return [
                Task(
                    goal="查询东京天气",
                    input="请提供东京未来一周的天气概况与出行建议。",
                    metadata={"task_type": "weather"},
                ),
                Task(
                    goal="推荐东京景点",
                    input="请推荐东京主要景点与每日游览建议。",
                    metadata={"task_type": "travel"},
                ),
                Task(
                    goal="查询东京酒店",
                    input="请推荐东京不同预算区间的酒店选择。",
                    metadata={"task_type": "hotel"},
                ),
            ]

        agent = self._router.route(
            root_task.input,
            self._registry,
            root_task.metadata,
        )

        if agent is not None:

            return [
                Task(
                    goal=root_task.goal,
                    input=root_task.input,
                    metadata=root_task.metadata,
                )
            ]

        return [root_task]

    def _synthesize(
        self,
        session_id: str,
        root_task: Task,
        completed_results: list[tuple[str, str, AgentResult]],
    ) -> AgentResult:

        if not completed_results:

            return AgentResult(
                success=False,
                model="",
                content="No subtask results to synthesize.",
            )

        if len(completed_results) == 1:

            _, _, result = completed_results[0]

            return result

        summary_agent = self._registry.get_agent(
            "summary"
        )

        summary_lines = [
            f"[{agent_name}] {goal}:\n{result.content}"
            for agent_name, goal, result in completed_results
            if result.success
        ]

        synthesis_input = (
            f"用户目标：{root_task.goal}\n\n"
            "以下是各 Agent 的执行结果，请汇总为一份完整、"
            "结构清晰的最终建议：\n\n"
            + "\n\n".join(summary_lines)
        )

        if summary_agent is not None:

            context = AgentContext(
                session_id=session_id,
                user_message=synthesis_input,
                metadata={
                    "current_task": "汇总最终答案",
                    "root_goal": root_task.goal,
                },
                agent_name="summary",
                shared_context=self._shared_memory.get_context_snapshot(),
            )

            return summary_agent.run(context)

        combined = (
            f"## {root_task.goal}\n\n"
            + "\n\n".join(
                f"### {goal}\n{result.content}"
                for _, goal, result in completed_results
                if result.success
            )
        )

        return AgentResult(
            success=True,
            model="coordinator",
            content=combined,
        )
