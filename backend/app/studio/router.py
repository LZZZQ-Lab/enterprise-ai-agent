"""
Agent Studio REST API（Task 6.8）。

路径: GET /workflow, /trace, /prompt, /memory 及调试辅助接口。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from app.studio.schemas import AgentStatusResponse
from app.studio.schemas import MemoryViewResponse
from app.studio.schemas import PromptViewResponse
from app.studio.schemas import RerunStepRequest
from app.studio.schemas import ToolsViewResponse
from app.studio.schemas import TraceViewResponse
from app.studio.schemas import UpdatePromptRequest
from app.studio.schemas import WorkflowViewResponse
from app.studio.service import default_studio_service

router = APIRouter(tags=["Agent Studio"])


@router.get("/workflow", response_model=WorkflowViewResponse)
def get_workflow(
    workflow_id: str | None = Query(None),
    run_id: str | None = Query(None),
) -> WorkflowViewResponse:
    try:
        return default_studio_service.get_workflow(
            workflow_id=workflow_id,
            run_id=run_id,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/trace", response_model=TraceViewResponse)
def get_trace(
    trace_id: str | None = Query(None),
    session_id: str | None = Query(None),
) -> TraceViewResponse:
    try:
        return default_studio_service.get_trace(
            trace_id=trace_id,
            session_id=session_id,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/prompt", response_model=PromptViewResponse)
def get_prompt(
    prompt_id: str = Query(...),
    version: str | None = Query(None),
) -> PromptViewResponse:
    try:
        return default_studio_service.get_prompt(
            prompt_id=prompt_id,
            version=version,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/memory", response_model=MemoryViewResponse)
def get_memory(
    session_id: str = Query(...),
    project_id: str | None = Query(None),
) -> MemoryViewResponse:
    return default_studio_service.get_memory(
        session_id=session_id,
        project_id=project_id,
    )


@router.get("/tools", response_model=ToolsViewResponse)
def get_tools() -> ToolsViewResponse:
    return default_studio_service.list_tools()


@router.get("/agent/status", response_model=AgentStatusResponse)
def get_agent_status(
    run_id: str = Query(...),
) -> AgentStatusResponse:
    try:
        return default_studio_service.get_agent_status(run_id=run_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/workflow/rerun", response_model=WorkflowViewResponse)
def rerun_workflow_step(body: RerunStepRequest) -> WorkflowViewResponse:
    try:
        return default_studio_service.rerun_step(
            run_id=body.run_id,
            node_id=body.node_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/prompt", response_model=PromptViewResponse)
def update_prompt(body: UpdatePromptRequest) -> PromptViewResponse:
    return default_studio_service.update_prompt(
        prompt_id=body.prompt_id,
        version=body.version,
        content=body.content,
    )
