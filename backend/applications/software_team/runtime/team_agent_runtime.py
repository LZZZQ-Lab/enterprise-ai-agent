from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm.factory import get_llm_client
from app.memory.manager import MemoryManager
from app.agents.executor.agent_executor import AgentExecutor
from app.config import AgentConfig
from app.agents.executor.error_handler import AgentErrorHandler
from app.agents.executor.observation_builder import ObservationBuilder
from app.agents.executor.tool_message_builder import ToolMessageBuilder
from app.agents.executor.tracer import AgentTracer
from app.tools.manager import ToolManager

from applications.software_team.config.settings import SoftwareTeamSettings
from applications.software_team.tools.registrar import register_team_tools

if TYPE_CHECKING:

    from app.llm.client import LLMClient


class TeamAgentRuntime:
    """
    Software Team Agent 运行时。

    组合 Framework 的 LLMClient、ToolManager、AgentExecutor，
    供所有 BaseTeamAgent 共享，避免重复初始化。
    """

    def __init__(
        self,
        settings: SoftwareTeamSettings | None = None,
        config: AgentConfig | None = None,
        memory_manager: MemoryManager | None = None,
        client: LLMClient | None = None,
        tool_manager: ToolManager | None = None,
        agent_executor: AgentExecutor | None = None,
        tracer: AgentTracer | None = None,
    ):

        self.settings = settings or SoftwareTeamSettings()
        self.config = config or self._build_config()

        register_team_tools()

        self.memory_manager = memory_manager or MemoryManager()
        self.tracer = tracer or AgentTracer()

        self.tool_manager = tool_manager or ToolManager(
            config=self.config,
            tracer=self.tracer,
        )

        self.client = client or get_llm_client()
        self.client.bind_tool_manager(self.tool_manager)

        observation_builder = ObservationBuilder()

        self.agent_executor = agent_executor or AgentExecutor(
            client=self.client,
            config=self.config,
            tool_message_builder=ToolMessageBuilder(
                observation_builder=observation_builder,
            ),
            tool_manager=self.tool_manager,
            error_handler=AgentErrorHandler(),
            tracer=self.tracer,
        )

    def _build_config(self) -> AgentConfig:

        return AgentConfig(
            max_iterations=self.settings.max_loop_iterations,
            enable_rag=self.settings.enable_rag,
            enable_mcp=self.settings.enable_mcp_tools,
            enable_trace=self.settings.enable_trace,
            system_prompt=None,
            system_prompt_path=None,
        )
