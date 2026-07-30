"""
Inference Gateway REST API（OpenAI 兼容 chat/completions）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import Field

from app.gateway.exceptions import GatewayError
from app.gateway.service import get_inference_gateway
from app.gateway.stats import get_token_stats
from app.gateway.types import TokenStatsSnapshot
from app.llm.types import Message

router = APIRouter(prefix="/inference", tags=["Inference Gateway"])


class ChatMessagePayload(BaseModel):
    role: str
    content: str | None = ""
    name: str | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessagePayload]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    tools: list[dict[str, Any]] | None = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: dict[str, Any]
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int]
    gateway: dict[str, Any] = Field(default_factory=dict)


@router.get("/stats", response_model=TokenStatsSnapshot)
def inference_token_stats() -> TokenStatsSnapshot:
    return get_token_stats()


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
):
    if body.stream:
        raise HTTPException(
            status_code=501,
            detail="stream=true not supported on gateway REST yet",
        )

    messages = [
        Message(
            role=item.role,
            content=item.content or "",
            name=item.name,
            tool_call_id=item.tool_call_id,
        )
        for item in body.messages
    ]

    gateway = get_inference_gateway()
    try:
        payload = gateway.chat(
            messages,
            use_tools=bool(body.tools),
        )
    except GatewayError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    result = payload.result
    message: dict[str, Any] = {
        "role": "assistant",
        "content": result.content or "",
    }
    if result.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": __import__("json").dumps(
                        call.arguments,
                        ensure_ascii=False,
                    ),
                },
            }
            for call in result.tool_calls
        ]

    response = ChatCompletionResponse(
        id=f"gw-{payload.meta.request_id}",
        model=result.model or payload.meta.model,
        choices=[
            ChatCompletionChoice(
                message=message,
                finish_reason=(
                    "tool_calls" if result.tool_calls else "stop"
                ),
            )
        ],
        usage={
            "prompt_tokens": payload.meta.usage.prompt_tokens,
            "completion_tokens": payload.meta.usage.completion_tokens,
            "total_tokens": payload.meta.usage.total_tokens,
        },
        gateway={
            "request_id": payload.meta.request_id,
            "backend": payload.meta.backend.value,
            "duration_ms": payload.meta.duration_ms,
        },
    )
    return response.model_dump()

