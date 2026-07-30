"""Task 8.6: security approval API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field

from security.auth import PermissionChecker
from security.auth import get_current_user_id
from security.guard import approval_store

router = APIRouter(prefix="/security", tags=["Security"])


class ApprovalActionRequest(BaseModel):
    action: str = Field(..., description="approve | reject")
    comment: str = ""


class ApprovalResponse(BaseModel):
    approval_id: str
    status: str
    tool_name: str
    approval_token: str | None = None
    message: str = ""


@router.get("/approvals/pending")
def list_pending_approvals() -> list[dict[str, Any]]:
    PermissionChecker.require("security_approve")
    return [
        {
            "approval_id": r.approval_id,
            "tool_name": r.tool_name,
            "arguments": r.arguments,
            "requested_by": r.requested_by,
            "created_at": r.created_at,
            "status": r.status.value,
        }
        for r in approval_store.list_pending()
    ]


@router.post("/approvals/{approval_id}", response_model=ApprovalResponse)
def resolve_approval(approval_id: str, body: ApprovalActionRequest) -> ApprovalResponse:
    PermissionChecker.require("security_approve")
    approver = get_current_user_id() or "admin"

    action = body.action.strip().lower()
    try:
        if action == "approve":
            req = approval_store.approve(approval_id, approver)
            return ApprovalResponse(
                approval_id=req.approval_id,
                status=req.status.value,
                tool_name=req.tool_name,
                approval_token=req.approval_token,
                message="Approved. Pass approval_token on next tool execution.",
            )
        if action == "reject":
            req = approval_store.reject(approval_id, approver, body.comment)
            return ApprovalResponse(
                approval_id=req.approval_id,
                status=req.status.value,
                tool_name=req.tool_name,
                message="Rejected.",
            )
    except KeyError:
        raise HTTPException(status_code=404, detail="approval not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="action must be approve or reject")
