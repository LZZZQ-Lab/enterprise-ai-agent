from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from pathlib import Path
from typing import Any


DEFAULT_SYSTEM_PROMPT_PATH = (
    Path(__file__)
    .resolve()
    .parent.parent
    / "prompts"
    / "templates"
    / "system.txt"
)


@dataclass
class AgentConfig:
    """
    Agent 运行时配置。

    控制 Agent Loop、Tool、MCP、RAG、Planner 等行为。
    生产环境请使用 AgentConfig.from_env() 从 Settings 加载。
    """

    max_iterations: int = 5

    temperature: float | None = None

    tool_choice: str = "auto"

    system_prompt: str | None = None

    system_prompt_path: Path | None = field(
        default_factory=lambda: DEFAULT_SYSTEM_PROMPT_PATH,
    )

    enable_rag: bool = False

    enable_knowledge_tool: bool = False

    top_k: int = 3

    score_threshold: float = 0.0

    enable_mcp: bool = False

    mcp_servers: list[str] = field(
        default_factory=list,
    )

    auto_discover_tools: bool = True

    auto_discover_resources: bool = True

    enable_mcp_prompts: bool = False

    mcp_prompt_name: str | None = None

    enable_planner: bool = False

    max_plan_steps: int = 10

    planner_model: str | None = None

    workflow_mode: str = "sequential"

    step_max_retries: int = 1

    enable_trace: bool = False

    enable_metrics: bool = False

    enable_evaluation: bool = False

    exporter_type: str = "console"

    enable_multi_agent: bool = False

    router_type: str = "rule"

    max_agents: int = 10

    communication_mode: str = "direct"

    enable_embodied: bool = False

    @classmethod
    def from_env(
        cls,
        **overrides: Any,
    ) -> "AgentConfig":
        """
        从统一 Settings 加载 Agent 配置。
        """

        from app.config.settings import get_settings

        app_settings = get_settings()

        base = cls(
            max_iterations=app_settings.MAX_AGENT_LOOP,
            temperature=app_settings.TEMPERATURE,
            planner_model=app_settings.MODEL_NAME,
            top_k=app_settings.RAG_TOP_K,
            score_threshold=app_settings.RAG_SCORE_THRESHOLD,
            enable_knowledge_tool=app_settings.ENABLE_KNOWLEDGE_TOOL,
            enable_mcp=app_settings.ENABLE_MCP,
            mcp_servers=app_settings.resolve_mcp_servers(),
            enable_trace=app_settings.ENABLE_AGENT_TRACE,
            exporter_type=app_settings.TRACE_EXPORTER,
        )

        if overrides:

            return replace(base, **overrides)

        return base
