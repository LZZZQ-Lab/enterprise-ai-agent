from __future__ import annotations

import json
import re
import time
from collections.abc import Generator

from openai import APIConnectionError
from openai import APIStatusError
from openai import APITimeoutError
from openai import InternalServerError
from openai import OpenAI

from app.config.settings import get_settings
from app.core.logger import logger
from app.llm.base import BaseLLM
from app.model_registry.provider_bridge import effective_max_tokens
from app.model_registry.provider_bridge import resolve_llm_model
from app.router.integration import route_for_messages
from app.llm.types import ChatResult
from app.llm.types import Message
from app.llm.types import ToolCall


class OpenAIProvider(BaseLLM):
    """
    OpenAI 兼容 API Provider。

    支持 OpenAI 官方及兼容网关（如 DeepSeek、Azure OpenAI 等）。
    """

    _TRANSIENT_STATUS_CODES = frozenset({429, 502, 503, 504})
    _MAX_ATTEMPTS = 6
    _MAX_REQUEST_CHARS = 100_000
    _MAX_TOOL_MESSAGE_CHARS = 4_000
    _MAX_HISTORY_MESSAGE_CHARS = 4_000

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        max_tokens: int | None = None,
    ) -> None:

        super().__init__()

        app_settings = get_settings()
        model_info = resolve_llm_model(
            model_name,
            default_name=app_settings.MODEL_NAME,
        )

        self._model_info = model_info
        self._model_name = model_info.model_id
        self._max_tokens = effective_max_tokens(
            explicit=max_tokens,
            settings_default=app_settings.MAX_TOKENS,
            model_info=model_info,
        )
        self._last_routing_report = None

        self.client = OpenAI(
            api_key=(
                api_key
                if api_key is not None
                else app_settings.API_KEY
            ),
            base_url=(
                base_url
                if base_url is not None
                else app_settings.OPENAI_BASE_URL
            ),
            max_retries=2,
            timeout=180.0,
        )

    @property
    def model_info(self):
        return self._model_info

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def last_routing_report(self):
        return getattr(self, "_last_routing_report", None)

    def _resolve_use_tools(self, use_tools: bool) -> bool:
        """
        子类可覆盖以调整是否向模型发送 tools（如 vLLM 默认关闭）。
        """

        return use_tools

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:

        logger.info("Calling LLM...")

        use_tools = self._resolve_use_tools(use_tools)

        trimmed_messages = self._trim_messages_for_request(messages)
        payload_chars = self._estimate_messages_chars(trimmed_messages)

        logger.info(
            "LLM request size: %d message(s), ~%d chars, tools=%s",
            len(trimmed_messages),
            payload_chars,
            use_tools,
        )

        app_settings = get_settings()

        active_model = self._model_name
        routing_report = route_for_messages(
            trimmed_messages,
            app_settings,
        )
        if routing_report is not None:
            active_model = routing_report.selected_model.model_id
            self._last_routing_report = routing_report
            logger.info("Model router: %s", routing_report.summary())
        else:
            self._last_routing_report = None

        request_kwargs = {
            "model": active_model,
            "messages": [
                self._serialize_message(message)
                for message in trimmed_messages
            ],
            "temperature": app_settings.TEMPERATURE,
            "max_tokens": self._max_tokens,
        }

        if use_tools:

            request_kwargs["tools"] = self._get_tool_schemas()
            request_kwargs["tool_choice"] = "auto"

        response = self._create_completion_with_retry(
            request_kwargs
        )

        logger.info("LLM Finished.")

        message = response.choices[0].message

        if message.tool_calls:

            tool_calls = self._build_tool_calls(message.tool_calls)

            if tool_calls:

                return ChatResult(
                    model=response.model,
                    content=message.content,
                    tool_calls=tool_calls,
                )

            if message.content:

                logger.warning(
                    "Dropped invalid tool_calls; falling back to text content"
                )

        return ChatResult(
            model=response.model,
            content=message.content,
        )

    def stream_chat(
        self,
        messages: list[Message],
    ) -> Generator[str, None, None]:

        app_settings = get_settings()

        trimmed = self._trim_messages_for_request(messages)
        active_model = self._model_name
        report = route_for_messages(trimmed, app_settings)
        if report is not None:
            active_model = report.selected_model.model_id
            self._last_routing_report = report

        response = self.client.chat.completions.create(
            model=active_model,
            messages=[
                self._serialize_message(message)
                for message in messages
            ],
            stream=True,
            temperature=app_settings.TEMPERATURE,
            max_tokens=self._max_tokens,
        )

        for chunk in response:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content

            if delta:

                yield delta

    def _build_tool_calls(
        self,
        raw_tool_calls,
    ) -> list[ToolCall]:

        tool_calls: list[ToolCall] = []

        for tool_call in raw_tool_calls:

            arguments = self._parse_arguments(
                tool_call.function.name,
                tool_call.function.arguments,
            )

            if not arguments:

                logger.warning(
                    "Skipping tool call %s due to empty/invalid arguments",
                    tool_call.function.name,
                )
                continue

            tool_calls.append(
                ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=arguments,
                )
            )

        return tool_calls

    def _create_completion_with_retry(
        self,
        request_kwargs: dict,
    ):
        last_error: Exception | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):

            try:

                return self.client.chat.completions.create(
                    **request_kwargs
                )

            except APIStatusError as error:

                last_error = error

                if (
                    not self._is_transient_error(error)
                    or attempt >= self._MAX_ATTEMPTS
                ):

                    raise

                delay_seconds = min(2 ** (attempt - 1), 16)

                logger.warning(
                    "LLM transient error %s (attempt %s/%s), retry in %ss",
                    getattr(error, "status_code", "unknown"),
                    attempt,
                    self._MAX_ATTEMPTS,
                    delay_seconds,
                )
                time.sleep(delay_seconds)

            except Exception as error:

                last_error = error

                if (
                    not self._is_transient_error(error)
                    or attempt >= self._MAX_ATTEMPTS
                ):

                    raise

                delay_seconds = min(2 ** (attempt - 1), 16)

                logger.warning(
                    "LLM transient error %s (attempt %s/%s), retry in %ss",
                    error,
                    attempt,
                    self._MAX_ATTEMPTS,
                    delay_seconds,
                )
                time.sleep(delay_seconds)

        if last_error is not None:

            raise last_error

        raise RuntimeError("LLM request failed without response")

    @classmethod
    def _is_transient_error(cls, error: Exception) -> bool:

        if isinstance(error, (APIConnectionError, APITimeoutError)):

            return True

        if isinstance(error, (APIStatusError, InternalServerError)):

            status_code = getattr(error, "status_code", None)

            if status_code in cls._TRANSIENT_STATUS_CODES:

                return True

        lowered = str(error).lower()

        return any(
            marker in lowered
            for marker in (
                "502",
                "503",
                "504",
                "429",
                "upstream",
                "timeout",
                "connection error",
            )
        )

    @classmethod
    def _estimate_messages_chars(cls, messages: list[Message]) -> int:

        total = 0

        for message in messages:

            total += len(message.content or "")

            if message.tool_calls:

                for tool_call in message.tool_calls:

                    total += len(
                        json.dumps(
                            tool_call.arguments,
                            ensure_ascii=False,
                        )
                    )

        return total

    def _trim_messages_for_request(
        self,
        messages: list[Message],
    ) -> list[Message]:

        if self._estimate_messages_chars(messages) <= self._MAX_REQUEST_CHARS:

            return messages

        logger.warning(
            "LLM payload exceeds %d chars, trimming message content",
            self._MAX_REQUEST_CHARS,
        )

        trimmed: list[Message] = []

        for message in messages:

            content = message.content

            if content and message.role == "tool":

                content = self._truncate_text(
                    content,
                    self._MAX_TOOL_MESSAGE_CHARS,
                    label="tool observation",
                )

            elif content and message.role in {"assistant", "user"}:

                content = self._truncate_text(
                    content,
                    self._MAX_HISTORY_MESSAGE_CHARS,
                    label="history",
                )

            trimmed.append(
                Message(
                    role=message.role,
                    content=content,
                    tool_call_id=message.tool_call_id,
                    name=message.name,
                    tool_calls=message.tool_calls,
                )
            )

        if self._estimate_messages_chars(trimmed) <= self._MAX_REQUEST_CHARS:

            return trimmed

        kept = trimmed[:2] + trimmed[-18:]

        logger.warning(
            "LLM payload still too large, keeping first 2 and last 18 messages"
        )

        return kept

    @staticmethod
    def _truncate_text(
        content: str,
        limit: int,
        *,
        label: str,
    ) -> str:

        if len(content) <= limit:

            return content

        return (
            f"{content[:limit]}\n\n"
            f"...[{label} truncated {len(content) - limit} chars]"
        )

    def _serialize_message(
        self,
        message: Message,
    ) -> dict:

        payload: dict = {
            "role": message.role,
        }

        if message.content is not None:

            payload["content"] = message.content

        if message.tool_call_id:

            payload["tool_call_id"] = message.tool_call_id

        if message.name:

            payload["name"] = message.name

        if message.tool_calls:

            payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(
                            tool_call.arguments,
                            ensure_ascii=False,
                        ),
                    },
                }
                for tool_call in message.tool_calls
            ]

        return payload

    @staticmethod
    def _parse_arguments(
        tool_name: str,
        raw_arguments: str | None,
    ) -> dict:

        if not raw_arguments:

            return {}

        try:

            parsed = json.loads(raw_arguments)

            if isinstance(parsed, dict):

                return parsed

            return {}

        except json.JSONDecodeError as error:

            recovered = OpenAIProvider._recover_tool_arguments(
                tool_name,
                raw_arguments,
            )

            if recovered:

                logger.warning(
                    "Recovered malformed %s arguments after JSON error: %s",
                    tool_name,
                    error,
                )
                return recovered

            logger.warning(
                "Failed to parse %s arguments: %s; preview=%s",
                tool_name,
                error,
                raw_arguments[:200],
            )
            return {}

    @staticmethod
    def _recover_tool_arguments(
        tool_name: str,
        raw_arguments: str,
    ) -> dict:

        path_match = re.search(
            r'"path"\s*:\s*"((?:\\.|[^"\\])*)"',
            raw_arguments,
        )

        if tool_name == "read_file" and path_match:

            return {
                "path": json.loads(f'"{path_match.group(1)}"'),
            }

        if tool_name != "write_file" or not path_match:

            return {}

        path = json.loads(f'"{path_match.group(1)}"')
        content_key = re.search(r'"content"\s*:\s*"', raw_arguments)

        if not content_key:

            return {"path": path, "content": ""}

        start = content_key.end()
        raw_content = raw_arguments[start:]
        content = OpenAIProvider._unescape_partial_json_string(raw_content)

        return {
            "path": path,
            "content": content,
        }

    @staticmethod
    def _unescape_partial_json_string(raw_content: str) -> str:
        """
        从不完整/损坏的 JSON 字符串值中尽量提取文本内容。
        """

        decoded: list[str] = []
        index = 0

        while index < len(raw_content):

            char = raw_content[index]

            if char == "\\" and index + 1 < len(raw_content):

                escaped = raw_content[index + 1]

                if escaped == "n":
                    decoded.append("\n")
                elif escaped == "t":
                    decoded.append("\t")
                elif escaped == "r":
                    decoded.append("\r")
                elif escaped == '"':
                    decoded.append('"')
                elif escaped == "\\":
                    decoded.append("\\")
                else:
                    decoded.append(escaped)

                index += 2
                continue

            if char == '"':

                break

            decoded.append(char)
            index += 1

        return "".join(decoded)
