from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile

from app.schemas.knowledge import KnowledgeAskRequest
from app.schemas.knowledge import KnowledgeAskResponse
from app.schemas.knowledge import KnowledgeUploadResponse
from app.services.knowledge_assistant_service import (
    knowledge_assistant_service,
)

router = APIRouter()


@router.post(
    "/documents",
    response_model=KnowledgeUploadResponse,
    summary="上传企业文档并建立知识库索引",
)
async def upload_document(
    file: UploadFile = File(...),
) -> KnowledgeUploadResponse:

    return knowledge_assistant_service.upload_document(
        file,
    )


@router.post(
    "/ask",
    response_model=KnowledgeAskResponse,
    summary="企业知识问答（Agent 检索 + LLM 生成）",
)
def ask_knowledge(
    request: KnowledgeAskRequest,
) -> KnowledgeAskResponse:

    return knowledge_assistant_service.ask(
        session_id=request.session_id,
        question=request.question,
    )
