from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any

from app.memory.types import MemoryRecord

if TYPE_CHECKING:
    from app.embodied.types import Observation
    from app.agents.executor.plan.types import Plan
    from app.agents.executor.plan.types import PlanStep


@dataclass
class AgentContext:
    """
    Agent 执行上下文
    """

    session_id: str

    user_message: str

    history: list[MemoryRecord] = field(
        default_factory=list
    )

    plan: "Plan | None" = None

    current_step: "PlanStep | None" = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    agent_name: str = ""

    agent_role: str = ""

    shared_context: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class AgentResult:
    """
    Agent 返回结果
    """

    success: bool

    model: str

    content: str

    observations: list["Observation"] = field(
        default_factory=list,
    )
