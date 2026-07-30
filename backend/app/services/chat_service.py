from __future__ import annotations

import time

from app.agents.runtime import AgentTask
from app.agents.runtime import default_runtime

from app.monitoring.metrics import infra_metrics
from app.monitoring.tokens import estimate_token_count
from app.schemas.chat import ChatResponse
from app.config.settings import get_settings


class ChatService:

    def __init__(
        self,
        runtime=None,
    ) -> None:

        self._runtime = runtime or default_runtime

    def chat(
        self,
        session_id: str,
        user_message: str,
    ) -> ChatResponse:

        settings = get_settings()

        if settings.ENABLE_INPUT_VALIDATION:
            from security.validator import InputValidator

            validator = InputValidator(
                max_message_length=settings.MAX_USER_MESSAGE_LENGTH,
            )
            check = validator.validate_chat_message(user_message)
            if not check.ok:
                return ChatResponse(
                    success=False,
                    model="security-validator",
                    answer=f"输入未通过安全校验：{check.reason}",
                )
            user_message = check.sanitized

        if settings.ENABLE_PROMPT_INJECTION_GUARD:
            from security.guard import PromptInjectionGuard

            guard = PromptInjectionGuard()
            scan = guard.scan(user_message)
            if not scan.allowed:
                return ChatResponse(
                    success=False,
                    model="security-guard",
                    answer="检测到可疑 Prompt Injection，请求已拒绝。",
                )

        from observability.logging.context import set_agent_id
        from observability.logging.context import set_session_id

        set_session_id(session_id)
        set_agent_id("chat")

        start = time.perf_counter()

        task = AgentTask(
            session_id=session_id,
            user_message=user_message,
            agent_name="chat",
        )

        result = self._runtime.run(task)

        duration = time.perf_counter() - start
        latency_ms = duration * 1000.0
        prompt_tokens = estimate_token_count(user_message)
        completion_tokens = estimate_token_count(result.content)
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        infra_metrics.record_llm_usage(
            model=result.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_sec=duration,
        )

        if settings.ENABLE_STRUCTURED_LOGGING:
            from observability.logging.logger import log_agent_execution

            log_agent_execution(
                agent_id="chat",
                token_usage=token_usage,
                latency_ms=latency_ms,
                model=result.model,
                success=result.success,
            )

        return ChatResponse(
            success=result.success,
            model=result.model,
            answer=result.content,
        )
