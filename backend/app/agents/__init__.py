from app.agents.base import BaseAgent
from app.agents.chat_agent import ChatAgent
from app.agents.factory import AgentFactory
from app.agents.manager_agent import ManagerAgent
from app.agents.software_team.devops_agent import DevOpsAgent
from app.agents.software_team.tester_agent import TesterAgent
from app.agents.software_team.reviewer_agent import ReviewerAgent
from app.agents.software_team.developer_agent import DeveloperAgent
from app.agents.software_team.architecture_agent import ArchitectureAgent
from app.agents.software_team.product_agent import ProductRequirementAgent
from app.agents.registry import AgentRegistry
from app.agents.registry import registry
from app.agents.runtime import AgentRuntime
from app.agents.runtime import AgentTask
from app.agents.runtime import default_runtime


registry.register(
    "chat",
    ChatAgent,
)

registry.register(
    "manager",
    ManagerAgent,
)

registry.register(
    "product",
    ProductRequirementAgent,
)

registry.register(
    "architecture",
    ArchitectureAgent,
)

registry.register(
    "developer",
    DeveloperAgent,
)

registry.register(
    "reviewer",
    ReviewerAgent,
)

registry.register(
    "tester",
    TesterAgent,
)

registry.register(
    "devops",
    DevOpsAgent,
)

__all__ = [
    "AgentFactory",
    "AgentRegistry",
    "AgentRuntime",
    "AgentTask",
    "BaseAgent",
    "ChatAgent",
    "ManagerAgent",
    "DevOpsAgent",
    "TesterAgent",
    "ReviewerAgent",
    "DeveloperAgent",
    "ArchitectureAgent",
    "ProductRequirementAgent",
    "default_runtime",
    "registry",
]
