"""Agent Studio API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import Field


class WorkflowViewResponse(BaseModel):
    workflow_id: str
    run_id: str | None = None
    name: str = ""
    description: str = ""
    status: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    node_results: dict[str, Any] = Field(default_factory=dict)
    pending_node_id: str | None = None


class TraceViewResponse(BaseModel):
    trace_id: str
    session_id: str = ""
    duration_sec: float | None = None
    timeline: str = ""
    events: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class PromptViewResponse(BaseModel):
    prompt_id: str
    version: str
    role: str = ""
    content: str = ""
    variables: list[str] = Field(default_factory=list)
    overridden: bool = False


class MemoryViewResponse(BaseModel):
    session_id: str
    project_id: str = ""
    conversation: list[dict[str, Any]] = Field(default_factory=list)
    project_memory: dict[str, str] = Field(default_factory=dict)
    shared: list[dict[str, Any]] = Field(default_factory=list)
    knowledge: list[dict[str, Any]] = Field(default_factory=list)


class ToolViewItem(BaseModel):
    name: str
    description: str = ""
    tool_schema: dict[str, Any] = Field(default_factory=dict)


class ToolsViewResponse(BaseModel):
    tools: list[ToolViewItem] = Field(default_factory=list)


class AgentStatusResponse(BaseModel):
    run_id: str
    workflow_id: str = ""
    status: str = ""
    agents: dict[str, Any] = Field(default_factory=dict)
    pending_node_id: str | None = None


class RerunStepRequest(BaseModel):
    run_id: str
    node_id: str


class UpdatePromptRequest(BaseModel):
    prompt_id: str
    version: str = "1.0.0"
    content: str
