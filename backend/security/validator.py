"""Task 8.6: input validation and filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass

# 控制字符（保留换行/tab）
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# 常见 SQL / shell 注入片段（轻量规则）
_SUSPICIOUS_PATTERNS = re.compile(
    r"(?i)(;\s*(drop|delete|truncate|exec|system)\b|"
    r"\$\(.+\)|`[^`]+`|&&|\|\||<\?php|__import__\(|eval\s*\()",
)

# 路径穿越
_PATH_TRAVERSAL = re.compile(r"(\.\./|\.\.\\|%2e%2e)")

DEFAULT_MAX_MESSAGE_LENGTH = 8000
DEFAULT_MAX_TOOL_ARG_LENGTH = 4000


@dataclass
class ValidationResult:
    ok: bool
    sanitized: str
    reason: str = ""


class InputValidator:
    """用户输入与 Tool 参数过滤。"""

    def __init__(
        self,
        *,
        max_message_length: int = DEFAULT_MAX_MESSAGE_LENGTH,
        max_tool_arg_length: int = DEFAULT_MAX_TOOL_ARG_LENGTH,
        block_suspicious: bool = True,
    ) -> None:
        self.max_message_length = max_message_length
        self.max_tool_arg_length = max_tool_arg_length
        self.block_suspicious = block_suspicious

    def sanitize_text(self, text: str, *, max_length: int | None = None) -> ValidationResult:
        if text is None:
            return ValidationResult(ok=False, sanitized="", reason="empty_input")

        limit = max_length or self.max_message_length
        cleaned = _CONTROL_CHARS.sub("", str(text)).strip()

        if not cleaned:
            return ValidationResult(ok=False, sanitized="", reason="empty_after_sanitize")

        if len(cleaned) > limit:
            return ValidationResult(
                ok=False,
                sanitized=cleaned[:limit],
                reason=f"exceeds_max_length_{limit}",
            )

        if self.block_suspicious and _SUSPICIOUS_PATTERNS.search(cleaned):
            return ValidationResult(ok=False, sanitized=cleaned, reason="suspicious_pattern")

        if _PATH_TRAVERSAL.search(cleaned):
            return ValidationResult(ok=False, sanitized=cleaned, reason="path_traversal")

        return ValidationResult(ok=True, sanitized=cleaned)

    def validate_chat_message(self, message: str) -> ValidationResult:
        return self.sanitize_text(message, max_length=self.max_message_length)

    def validate_tool_arguments(self, arguments: dict) -> ValidationResult:
        import json

        try:
            payload = json.dumps(arguments, ensure_ascii=False)
        except (TypeError, ValueError):
            return ValidationResult(ok=False, sanitized="", reason="invalid_arguments")

        return self.sanitize_text(payload, max_length=self.max_tool_arg_length)
