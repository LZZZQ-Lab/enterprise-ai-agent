"""
Model Registry HTTP API（查询与动态注册）。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field

from app.model_registry.manager import get_model_registry_manager
from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor

router = APIRouter(prefix="/models", tags=["Model Registry"])


class RegisterModelRequest(ModelInfo):
    """与 ModelInfo 相同，用于 POST 注册。"""

    overwrite: bool = Field(
        default=False,
        description="若 name 已存在是否覆盖",
    )


class ReloadRegistryResponse(BaseModel):
    loaded: int
    path: str


@router.get("", response_model=list[ModelInfo])
def list_models(
    provider: ModelVendor | None = Query(default=None),
    capability: str | None = Query(default=None),
    name_prefix: str | None = Query(default=None),
) -> list[ModelInfo]:
    manager = get_model_registry_manager()
    return manager.query(
        provider=provider,
        capability=capability,
        name_prefix=name_prefix,
    )


@router.get("/{name}", response_model=ModelInfo)
def get_model(name: str) -> ModelInfo:
    manager = get_model_registry_manager()
    try:
        return manager.resolve(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=ModelInfo)
def register_model(body: RegisterModelRequest) -> ModelInfo:
    manager = get_model_registry_manager()
    payload = body.model_dump(exclude={"overwrite"})
    model = ModelInfo.model_validate(payload)
    try:
        manager.register(model, overwrite=body.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return model


@router.post("/reload", response_model=ReloadRegistryResponse)
def reload_registry() -> ReloadRegistryResponse:
    manager = get_model_registry_manager()
    loaded = manager.load_from_file(overwrite=True)
    path = str(manager.registry_path)
    return ReloadRegistryResponse(loaded=loaded, path=path)
