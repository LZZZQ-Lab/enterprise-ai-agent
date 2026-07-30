from pydantic import BaseModel
from pydantic import Field


class KnowledgeUploadResponse(BaseModel):
    """
    文档上传并入库结果。
    """

    success: bool

    file_name: str

    chunks_ingested: int

    message: str = ""


class KnowledgeAskRequest(BaseModel):
    """
    企业知识问答请求。
    """

    question: str = Field(..., min_length=1)

    session_id: str = "knowledge-demo"


class KnowledgeSourceItem(BaseModel):
    """
    检索到的知识片段。
    """

    document_id: str

    content: str

    score: float

    file_name: str | None = None


class KnowledgeAskResponse(BaseModel):
    """
    Agent + RAG 问答结果。
    """

    success: bool

    answer: str

    model: str = ""

    sources: list[KnowledgeSourceItem] = Field(
        default_factory=list
    )
