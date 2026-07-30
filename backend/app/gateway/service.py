"""
Inference Gateway 核心服务。
"""

from __future__ import annotations

import threading
import time
import uuid

from app.gateway.config import create_inference_backend
from app.gateway.config import resolve_backend_kind
from app.gateway.error_mapper import translate_exception
from app.gateway.logging_util import log_gateway_error
from app.gateway.logging_util import log_gateway_request
from app.gateway.logging_util import log_gateway_response
from app.gateway.stats import record_token_usage
from app.gateway.types import GatewayCallMeta
from app.gateway.types import GatewayChatResult
from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage
from app.llm.base import BaseLLM
from app.llm.types import Message

_gateway_lock = threading.Lock()
_default_gateway: InferenceGateway | None = None


class InferenceGateway:
    """
    统一推理入口：日志、Token 统计、异常映射。
    """

    def __init__(
        self,
        backend: BaseLLM | None = None,
        *,
        backend_kind: InferenceBackendKind | None = None,
        provider_name: str | None = None,
    ) -> None:
        self._backend = backend or create_inference_backend(provider_name)
        self._backend_kind = backend_kind or resolve_backend_kind(
            provider_name,
        )

    @property
    def backend_kind(self) -> InferenceBackendKind:
        return self._backend_kind

    @property
    def backend(self) -> BaseLLM:
        return self._backend

    def chat(
        self,
        messages: list[Message],
        *,
        use_tools: bool = True,
    ) -> GatewayChatResult:
        request_id = uuid.uuid4().hex
        model = getattr(self._backend, "model_id", "") or getattr(
            self._backend,
            "_model_name",
            "",
        )

        log_gateway_request(
            request_id=request_id,
            backend=self._backend_kind,
            model=str(model),
            message_count=len(messages),
            use_tools=use_tools,
        )

        self._refresh_discovered_backend_if_needed()

        started = time.perf_counter()

        active_model = str(
            getattr(self._backend, "model_id", None)
            or getattr(self._backend, "_model_name", model)
        )

        from app.cache.manager import cache_enabled
        from app.cache.manager import get_model_cache_manager

        if cache_enabled():
            cache_mgr = get_model_cache_manager()
            prompt_payload = [message.model_dump() for message in messages]
            if cache_mgr.prompt.get(model=active_model, messages=messages) is None:
                cache_mgr.prompt.set(
                    model=active_model,
                    messages=messages,
                    payload=prompt_payload,
                )

            cached = cache_mgr.response.get(
                model=active_model,
                messages=messages,
                use_tools=use_tools,
            )
            if cached is not None:
                duration_ms = (time.perf_counter() - started) * 1000.0
                meta = GatewayCallMeta(
                    request_id=request_id,
                    backend=self._backend_kind,
                    model=cached.model or active_model,
                    duration_ms=round(duration_ms, 2),
                    usage=TokenUsage(),
                    cache_hit=True,
                    cache_layer="response",
                )
                log_gateway_response(
                    request_id=request_id,
                    backend=self._backend_kind,
                    model=meta.model,
                    duration_ms=meta.duration_ms,
                    usage=meta.usage,
                    success=True,
                )
                return GatewayChatResult(result=cached, meta=meta)

        try:
            result = self._backend.chat(messages, use_tools=use_tools)
            duration_ms = (time.perf_counter() - started) * 1000.0

            usage = getattr(self._backend, "last_usage", None)
            if usage is None:
                usage = TokenUsage()
            elif hasattr(usage, "model_copy"):
                usage = usage.model_copy()
            else:
                usage = TokenUsage.model_validate(usage)

            active_model = result.model or active_model
            record_token_usage(
                backend=self._backend_kind,
                model=active_model,
                usage=usage,
            )

            if cache_enabled() and not use_tools:
                get_model_cache_manager().response.set(
                    model=active_model,
                    messages=messages,
                    result=result,
                )

            meta = GatewayCallMeta(
                request_id=request_id,
                backend=self._backend_kind,
                model=active_model,
                duration_ms=round(duration_ms, 2),
                usage=usage,
            )

            log_gateway_response(
                request_id=request_id,
                backend=self._backend_kind,
                model=active_model,
                duration_ms=meta.duration_ms,
                usage=usage,
                success=True,
            )

            return GatewayChatResult(result=result, meta=meta)

        except Exception as exc:
            log_gateway_error(
                request_id,
                exc,
                extra={"backend": self._backend_kind.value},
            )
            node_id = getattr(self._backend, "service_node_id", None)
            if node_id:
                try:
                    from app.config.settings import get_settings
                    from app.service.manager import get_service_discovery_manager

                    if get_settings().ENABLE_SERVICE_DISCOVERY:
                        get_service_discovery_manager().on_request_failure(
                            node_id,
                            reason=str(exc),
                        )
                except Exception:
                    pass
            mapped = translate_exception(exc, backend=self._backend_kind)
            log_gateway_response(
                request_id=request_id,
                backend=self._backend_kind,
                model=str(model),
                duration_ms=(time.perf_counter() - started) * 1000.0,
                usage=TokenUsage(),
                success=False,
                error_code=mapped.code,
            )
            raise mapped from exc

    def bind_tool_manager(self, tool_manager) -> None:
        self._backend.bind_tool_manager(tool_manager)

    def _refresh_discovered_backend_if_needed(self) -> None:
        from app.config.settings import get_settings

        app_settings = get_settings()
        if not app_settings.ENABLE_SERVICE_DISCOVERY:
            return
        if self._backend_kind not in {
            InferenceBackendKind.VLLM,
            InferenceBackendKind.SGLANG,
        }:
            return

        previous_tools = getattr(self._backend, "_tool_manager", None)
        self._backend = create_inference_backend(self._backend_kind.value)
        if previous_tools is not None:
            self._backend.bind_tool_manager(previous_tools)


def get_inference_gateway(
    provider_name: str | None = None,
) -> InferenceGateway:
    global _default_gateway

    with _gateway_lock:
        if _default_gateway is None:
            _default_gateway = InferenceGateway(provider_name=provider_name)
        return _default_gateway


def reset_inference_gateway() -> None:
    global _default_gateway

    with _gateway_lock:
        _default_gateway = None
