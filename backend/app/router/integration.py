"""Router 与 LLM Provider 集成。"""

from __future__ import annotations

from app.config.settings import Settings
from app.llm.types import Message
from app.router.engine import get_router_engine
from app.router.types import RoutingContext
from app.router.types import RoutingReport


def prompt_from_messages(messages: list[Message]) -> str:
    """拼接最近若干轮 user 内容供分类使用。"""

    user_parts: list[str] = []
    for message in reversed(messages):
        if message.role != "user":
            continue
        content = (message.content or "").strip()
        if content:
            user_parts.append(content)
        if len(user_parts) >= 3:
            break
    if not user_parts:
        return ""
    return "\n".join(reversed(user_parts))


def route_for_messages(
    messages: list[Message],
    settings: Settings,
    *,
    task: str | None = None,
    metadata: dict | None = None,
) -> RoutingReport | None:
    """
    若启用 MODEL_ROUTER，根据消息生成 RoutingReport；否则返回 None。
    """

    if not settings.ENABLE_MODEL_ROUTER:
        return None

    explicit_task = task
    if not explicit_task and metadata:
        explicit_task = metadata.get("task_type") or metadata.get("task")

    context = RoutingContext(
        prompt=prompt_from_messages(messages),
        task=explicit_task,
        prefer_low_cost=settings.MODEL_ROUTER_PREFER_LOW_COST,
        prefer_low_latency=settings.MODEL_ROUTER_PREFER_LOW_LATENCY,
        metadata=dict(metadata or {}),
    )
    return get_router_engine().route(context)
