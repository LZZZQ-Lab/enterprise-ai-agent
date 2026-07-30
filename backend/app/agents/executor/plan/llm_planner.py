import json
import re

from typing import TYPE_CHECKING

from app.llm.types import Message
from app.config import AgentConfig
from app.agents.executor.plan.planner import Planner
from app.agents.executor.plan.strategy import PlannerStrategy
from app.agents.executor.plan.strategy import SinglePlanStrategy
from app.agents.executor.plan.types import Plan
from app.agents.executor.plan.types import PlanStep
from app.agents.executor.plan.types import PlanStatus

if TYPE_CHECKING:
    from app.agents.types import AgentContext
    from app.llm.client import LLMClient


class LLMPlanner(Planner):
    """
    基于 LLM 的规划器。

    根据用户目标生成多步执行计划。
    """

    _PLANNING_SYSTEM_PROMPT = (
        "You are a planning assistant. Break down the user's "
        "goal into clear executable steps.\n"
        "Return ONLY valid JSON in this format:\n"
        '{"steps":[{"id":"step-1","description":"...",'
        '"tool":null}]}\n'
        "Use tool only when a specific tool name is clearly "
        "needed, otherwise set tool to null."
    )

    def __init__(
        self,
        client: "LLMClient",
        config: AgentConfig | None = None,
        strategy: PlannerStrategy | None = None,
    ):

        self._client = client
        self._config = config or AgentConfig.from_env()
        self._strategy = (
            strategy or SinglePlanStrategy()
        )

    def plan(
        self,
        context: "AgentContext",
    ) -> Plan:

        messages = [
            Message(
                role="system",
                content=self._PLANNING_SYSTEM_PROMPT,
            ),
            Message(
                role="user",
                content=context.user_message,
            ),
        ]

        try:

            result = self._client.chat(
                messages,
                use_tools=False,
            )

            raw_steps = self._parse_steps(
                result.content or ""
            )

            plan = self._strategy.build_plan(
                goal=context.user_message,
                raw_steps=raw_steps,
                config=self._config,
            )

            plan.metadata["planner"] = "llm"
            plan.metadata["model"] = result.model

            return plan

        except Exception as error:

            return Plan(
                goal=context.user_message,
                steps=[
                    PlanStep(
                        id="step-1",
                        description=context.user_message,
                    )
                ],
                status=PlanStatus.PENDING,
                metadata={
                    "planner": "llm_fallback",
                    "error": str(error),
                },
            )

    @staticmethod
    def _parse_steps(
        content: str,
    ) -> list[dict]:

        content = content.strip()

        if not content:

            return []

        try:

            payload = json.loads(content)

            steps = payload.get(
                "steps",
                [],
            )

            if isinstance(steps, list):

                return steps

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                content,
                re.DOTALL,
            )

            if match:

                payload = json.loads(match.group())

                return payload.get(
                    "steps",
                    [],
                )

        return []
