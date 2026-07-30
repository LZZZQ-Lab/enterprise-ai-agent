from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.agents.runtime import AgentTask
from app.agents.runtime import default_runtime
from app.config import AgentConfig
from app.config.settings import get_settings
from app.monitoring.metrics import infra_metrics
from app.monitoring.tokens import estimate_token_count
from app.rag.pipeline import create_rag_pipeline
from app.rag.types import SourceDocument
from app.schemas.knowledge import KnowledgeAskResponse
from app.schemas.knowledge import KnowledgeSourceItem
from app.schemas.knowledge import KnowledgeUploadResponse


class KnowledgeAssistantService:
    """
    企业知识助手：上传文档 → 建库 → Agent 检索 → LLM 回答。
    """

    _ALLOWED_SUFFIXES = frozenset(
        {".txt", ".md", ".markdown", ".pdf", ".docx"}
    )

    def __init__(
        self,
        runtime=None,
        pipeline=None,
    ) -> None:

        self._runtime = runtime or default_runtime
        self._pipeline = pipeline or create_rag_pipeline()

    @property
    def pipeline(self):

        return self._pipeline

    def upload_document(
        self,
        upload: UploadFile,
    ) -> KnowledgeUploadResponse:

        settings = get_settings()

        upload_dir = Path(
            settings.KNOWLEDGE_UPLOAD_DIR
        ).expanduser()

        upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        original_name = upload.filename or "document.txt"

        suffix = Path(original_name).suffix.lower()

        if suffix not in self._ALLOWED_SUFFIXES:

            return KnowledgeUploadResponse(
                success=False,
                file_name=original_name,
                chunks_ingested=0,
                message=(
                    f"Unsupported file type '{suffix}'. "
                    f"Allowed: {', '.join(sorted(self._ALLOWED_SUFFIXES))}"
                ),
            )

        stored_name = (
            f"{uuid.uuid4().hex[:12]}_{original_name}"
        )

        destination = upload_dir / stored_name

        with destination.open("wb") as output:

            shutil.copyfileobj(
                upload.file,
                output,
            )

        try:

            chunks = self._pipeline.ingest_file(
                destination,
                extra_metadata={
                    "upload_name": original_name,
                },
            )

        except Exception as error:

            destination.unlink(missing_ok=True)

            return KnowledgeUploadResponse(
                success=False,
                file_name=original_name,
                chunks_ingested=0,
                message=str(error),
            )

        return KnowledgeUploadResponse(
            success=True,
            file_name=original_name,
            chunks_ingested=chunks,
            message="Document ingested into knowledge base.",
        )

    def ask(
        self,
        session_id: str,
        question: str,
    ) -> KnowledgeAskResponse:

        sources = self._pipeline.retrieve(question)

        config = AgentConfig.from_env(
            enable_knowledge_tool=True,
            enable_mcp=False,
            enable_rag=False,
            enable_trace=get_settings().ENABLE_AGENT_TRACE,
            enable_planner=False,
        )

        start = time.perf_counter()

        result = self._runtime.run(
            AgentTask(
                session_id=session_id,
                user_message=question,
                agent_name="chat",
            ),
            config=config,
        )

        duration = time.perf_counter() - start

        infra_metrics.record_llm_usage(
            model=result.model,
            prompt_tokens=estimate_token_count(question),
            completion_tokens=estimate_token_count(
                result.content or "",
            ),
            duration_sec=duration,
        )

        return KnowledgeAskResponse(
            success=result.success,
            answer=result.content or "",
            model=result.model,
            sources=[
                self._source_to_schema(source)
                for source in sources
            ],
        )

    @staticmethod
    def _source_to_schema(
        source: SourceDocument,
    ) -> KnowledgeSourceItem:

        return KnowledgeSourceItem(
            document_id=source.document_id,
            content=source.content,
            score=source.score,
            file_name=source.metadata.get("file_name"),
        )


knowledge_assistant_service = KnowledgeAssistantService()
