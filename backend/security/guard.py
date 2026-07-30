"""Task 8.6: prompt injection guard and dangerous operation approval."""

from __future__ import annotations

import json
import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any

from security.auth import get_current_user_id

# Prompt injection 常见模式
_INJECTION_PATTERNS = re.compile(
    r"(?i)("
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|"
    r"disregard\s+(the\s+)?(system|developer)\s+prompt|"
    r"you\s+are\s+now\s+(dan|jailbreak|unrestricted)|"
    r"reveal\s+(the\s+)?(system|hidden)\s+prompt|"
    r"<\s*/?\s*system\s*>|"
    r"###\s*instruction\s*override"
    r")",
)

_DANGEROUS_TOOLS = frozenset(
    {
        "terminal",
        "code",
        "run_command",
        "execute",
        "shell",
        "write_file",
        "delete_file",
    }
)

_approval_token: ContextVar[str | None] = ContextVar("approval_token", default=None)


def set_approval_token(token: str | None) -> None:
    _approval_token.set(token)


def get_approval_token() -> str | None:
    return _approval_token.get()


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
    needs_approval: bool = False
    approval_id: str | None = None
    risk_score: float = 0.0


@dataclass
class ApprovalRequest:
    approval_id: str
    tool_name: str
    arguments: dict[str, Any]
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(default_factory=lambda: _now_iso())
    resolved_at: str | None = None
    approver: str | None = None
    approval_token: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class PromptInjectionGuard:
    """检测并阻断可疑 Prompt Injection。"""

    def __init__(self, *, block_threshold: float = 0.5) -> None:
        self.block_threshold = block_threshold

    def scan(self, text: str) -> GuardResult:
        if not text or not text.strip():
            return GuardResult(allowed=True)

        matches = list(_INJECTION_PATTERNS.finditer(text))
        if not matches:
            return GuardResult(allowed=True, risk_score=0.0)

        score = min(1.0, 0.4 + 0.2 * len(matches))
        if score >= self.block_threshold:
            return GuardResult(
                allowed=False,
                reason="prompt_injection_detected",
                risk_score=score,
            )
        return GuardResult(allowed=True, risk_score=score, reason="injection_warning")

    def wrap_untrusted_content(self, label: str, content: str) -> str:
        """为 RAG / 外部文本添加边界标记，降低注入影响。"""
        safe_label = re.sub(r"[^\w\-]", "_", label)[:32]
        return (
            f"<untrusted source=\"{safe_label}\">\n"
            f"{content}\n"
            f"</untrusted>"
        )


class ApprovalStore:
    """内存审批单（Demo / 单实例）。"""

    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRequest] = {}

    def create(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        requested_by: str,
    ) -> ApprovalRequest:
        approval_id = uuid.uuid4().hex[:16]
        req = ApprovalRequest(
            approval_id=approval_id,
            tool_name=tool_name,
            arguments=arguments,
            requested_by=requested_by,
        )
        self._pending[approval_id] = req
        return req

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._pending.get(approval_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return [
            r
            for r in self._pending.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def approve(self, approval_id: str, approver: str) -> ApprovalRequest:
        req = self._require_pending(approval_id)
        token = uuid.uuid4().hex
        req.status = ApprovalStatus.APPROVED
        req.approver = approver
        req.resolved_at = _now_iso()
        req.approval_token = token
        return req

    def reject(self, approval_id: str, approver: str, reason: str = "") -> ApprovalRequest:
        req = self._require_pending(approval_id)
        req.status = ApprovalStatus.REJECTED
        req.approver = approver
        req.resolved_at = _now_iso()
        if reason:
            req.arguments = {**req.arguments, "_reject_reason": reason}
        return req

    def consume_token(self, token: str, tool_name: str) -> bool:
        for req in self._pending.values():
            if (
                req.status == ApprovalStatus.APPROVED
                and req.approval_token == token
                and req.tool_name == tool_name
            ):
                req.status = ApprovalStatus.EXPIRED
                return True
        return False

    def _require_pending(self, approval_id: str) -> ApprovalRequest:
        req = self._pending.get(approval_id)
        if req is None:
            raise KeyError(f"approval not found: {approval_id}")
        if req.status != ApprovalStatus.PENDING:
            raise ValueError(f"approval not pending: {approval_id}")
        return req


# 全局单例（Demo）
approval_store = ApprovalStore()


class DangerousOperationGuard:
    """危险 Tool 执行前需 Admin 审批。"""

    def __init__(
        self,
        *,
        store: ApprovalStore | None = None,
        dangerous_tools: frozenset[str] | None = None,
        require_approval: bool = True,
    ) -> None:
        self.store = store or approval_store
        self.dangerous_tools = dangerous_tools or _DANGEROUS_TOOLS
        self.require_approval = require_approval

    def is_dangerous(self, tool_name: str) -> bool:
        normalized = tool_name.strip().lower()
        return normalized in self.dangerous_tools or any(
            d in normalized for d in self.dangerous_tools
        )

    def check_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        approval_token: str | None = None,
    ) -> GuardResult:
        if not self.require_approval or not self.is_dangerous(tool_name):
            return GuardResult(allowed=True)

        token = approval_token or get_approval_token()
        if token and self.store.consume_token(token, tool_name):
            return GuardResult(allowed=True, reason="approval_consumed")

        user_id = get_current_user_id() or "anonymous"
        pending = self.store.create(
            tool_name=tool_name,
            arguments=arguments,
            requested_by=user_id,
        )
        return GuardResult(
            allowed=False,
            needs_approval=True,
            approval_id=pending.approval_id,
            reason="dangerous_operation_requires_approval",
            risk_score=0.9,
        )


def check_tool_execution(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    prompt_guard: PromptInjectionGuard | None = None,
    danger_guard: DangerousOperationGuard | None = None,
    validator: Any | None = None,
) -> GuardResult | None:
    """
    统一 Tool 执行前安全检查。

    返回 GuardResult 表示应阻断；None 表示通过。
    """
    from security.validator import InputValidator

    val = validator or InputValidator()
    arg_check = val.validate_tool_arguments(arguments)
    if not arg_check.ok:
        return GuardResult(allowed=False, reason=f"invalid_tool_args:{arg_check.reason}")

    for value in arguments.values():
        if isinstance(value, str):
            inj = (prompt_guard or PromptInjectionGuard()).scan(value)
            if not inj.allowed:
                return inj

    danger = danger_guard or DangerousOperationGuard()
    danger_result = danger.check_tool(tool_name, arguments)
    if not danger_result.allowed:
        return danger_result

    return None


def format_approval_required_result(approval_id: str, tool_name: str) -> str:
    return json.dumps(
        {
            "status": "approval_required",
            "approval_id": approval_id,
            "tool_name": tool_name,
            "message": "危险操作需要 Admin 审批。请调用 POST /api/v1/security/approvals/{id}/approve",
        },
        ensure_ascii=False,
    )
