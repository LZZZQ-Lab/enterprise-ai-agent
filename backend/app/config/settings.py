from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import AliasChoices
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

if TYPE_CHECKING:
    from app.model_registry.models import ModelInfo


class Settings(BaseSettings):
    """
    企业级统一配置。

    所有模块（LLM Provider、Agent Loop、API）均从此处读取配置，
    禁止在业务代码中硬编码。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # ── App / API ──────────────────────────────────────────
    APP_NAME: str = "Enterprise AI Agent"
    APP_VERSION: str = Field(
        default="0.1.0",
        description="SemVer; overridden by VERSION file when unset in env",
    )
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    # Swagger UI 静态资源 CDN 前缀（默认 unpkg；国内可设 bootcdn 见 .env.example）
    SWAGGER_UI_CDN: str = "unpkg"

    # ── LLM Provider ───────────────────────────────────────
    MODEL_PROVIDER: str = Field(
        default="openai",
        validation_alias=AliasChoices(
            "MODEL_PROVIDER",
            "LLM_PROVIDER",
        ),
    )
    MODEL_NAME: str = "gpt-4o-mini"
    API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices(
            "API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4096
    MODEL_REGISTRY_PATH: str = ""
    ENABLE_MODEL_ROUTER: bool = False
    MODEL_ROUTER_PREFER_LOW_COST: bool = False
    MODEL_ROUTER_PREFER_LOW_LATENCY: bool = True
    MODEL_ROUTER_LONG_CONTEXT_CHARS: int = 6000

    ENABLE_INFERENCE_GATEWAY: bool = True
    INFERENCE_BACKEND: str = ""
    SGLANG_ENDPOINT: str = "http://localhost:30000/v1"
    SGLANG_API_KEY: str = "EMPTY"
    SGLANG_MAX_TOKENS: int = 4096
    TGI_ENDPOINT: str = "http://localhost:8080/v1"
    TGI_API_KEY: str = "EMPTY"
    TGI_MAX_TOKENS: int = 4096

    ENABLE_SERVICE_DISCOVERY: bool = True
    VLLM_NODES: str = ""
    SGLANG_NODES: str = ""
    SERVICE_HEALTH_TIMEOUT_SEC: float = 5.0
    SERVICE_STALE_AFTER_SEC: float = 45.0

    ENABLE_MODEL_CACHE: bool = True
    CACHE_BACKEND: str = "memory"
    CACHE_PROMPT_TTL_SEC: int = 86400
    CACHE_EMBEDDING_TTL_SEC: int = 604800
    CACHE_RESPONSE_TTL_SEC: int = 3600
    CACHE_MEMORY_MAX_ENTRIES: int = 10000

    # ── Agent Loop ─────────────────────────────────────────
    MAX_AGENT_LOOP: int = 5

    # ── Embedding (RAG) ───────────────────────────────────
    EMBEDDING_PROVIDER: str = "fake"
    EMBEDDING_MODEL: str = ""
    EMBEDDING_DIMENSION: int = 0
    LOCAL_EMBEDDING_MODEL_ID: str = "BAAI/bge-small-zh-v1.5"
    LOCAL_EMBEDDING_DEVICE: str = "cpu"

    # ── Vector Store (RAG) ─────────────────────────────────
    VECTOR_STORE_PROVIDER: str = "memory"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "enterprise_kb"
    CHROMA_HOST: str = ""
    CHROMA_PORT: int = 8000

    REDIS_URL: str = ""

    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.0
    ENABLE_KNOWLEDGE_TOOL: bool = True

    ENABLE_MCP: bool = False
    MCP_SERVERS: str = "enterprise-demo"
    MCP_SYNC_TO_REGISTRY: bool = True

    KNOWLEDGE_UPLOAD_DIR: str = "./data/knowledge_uploads"

    ENABLE_INFRA_METRICS: bool = True

    ENABLE_STRUCTURED_LOGGING: bool = True
    STRUCTURED_LOG_FILE: str = Field(
        default="",
        description="Optional NDJSON file for ELK/Loki ingestion",
    )
    LOG_SERVICE_NAME: str = "enterprise-ai-agent"

    ENABLE_AGENT_TRACE: bool = False

    # ── Security (Task 8.6) ────────────────────────────────
    ENABLE_API_AUTH: bool = False
    API_AUTH_TOKENS: str = Field(
        default="",
        description="Comma-separated token:role:user_id entries for API auth",
    )
    ENABLE_INPUT_VALIDATION: bool = True
    ENABLE_PROMPT_INJECTION_GUARD: bool = True
    ENABLE_DANGEROUS_TOOL_APPROVAL: bool = True
    MAX_USER_MESSAGE_LENGTH: int = 8000

    TRACE_EXPORTER: str = "structured"

    TRACE_EXPORT_DIR: str = "./artifacts/agent_traces"

    # ── Local Provider ─────────────────────────────────────
    LOCAL_MODEL_ID: str = "Qwen/Qwen2.5-0.5B-Instruct"
    LOCAL_MODEL_NAME: str = "Qwen/Qwen2.5-0.5B-Instruct"
    LOCAL_MODEL_DEVICE: str = "auto"
    LOCAL_MODEL_4BIT: bool = False
    LOCAL_MODEL_MAX_NEW_TOKENS: int = 512
    LOCAL_MODEL_BASE_URL: str = "http://127.0.0.1:8000/v1"

    def resolve_model_info(self, name: str | None = None) -> ModelInfo:
        """
        通过 Model Registry 解析 MODEL_NAME 或指定名称。
        """

        from app.model_registry.provider_bridge import resolve_llm_model

        return resolve_llm_model(
            name,
            default_name=self.MODEL_NAME,
        )

    def resolve_local_model_id(self) -> str:
        """
        解析本地 HuggingFace 模型 ID。

        优先 LOCAL_MODEL_ID；否则经 Model Registry 解析 MODEL_NAME。
        """

        if self.LOCAL_MODEL_ID:

            return self.LOCAL_MODEL_ID

        return self.resolve_model_info().model_id

    def resolve_vllm_model_id(self) -> str:
        """
        解析 vLLM 服务上的模型 ID（经 Model Registry）。
        """

        return self.resolve_model_info().model_id

    # ── vLLM Provider ──────────────────────────────────────
    VLLM_ENDPOINT: str = "http://localhost:8000/v1"
    VLLM_API_KEY: str = "EMPTY"
    VLLM_MAX_TOKENS: int = Field(
        default=256,
        description="Completion cap for vLLM; keep below server max_model_len minus prompt",
    )
    VLLM_ENABLE_TOOL_CALLING: bool = Field(
        default=False,
        description=(
            "Send tools/tool_choice to vLLM. Requires vLLM started with "
            "--enable-auto-tool-choice and --tool-call-parser (e.g. qwen)."
        ),
    )

    def resolve_mcp_servers(self) -> list[str]:
        """
        解析 MCP Server 名称列表。
        """

        raw = self.MCP_SERVERS.strip()

        if not raw:

            return ["local-mock"]

        return [
            part.strip()
            for part in raw.split(",")
            if part.strip()
        ]

    @property
    def LLM_PROVIDER(self) -> str:
        """向后兼容 Task 1.3 命名。"""

        return self.MODEL_PROVIDER

    @property
    def OPENAI_API_KEY(self) -> str:
        """向后兼容旧命名。"""

        return self.API_KEY


@lru_cache
def get_settings() -> Settings:

    import os

    from app.version import read_version

    settings = Settings()

    if os.getenv("APP_VERSION"):

        return settings

    return settings.model_copy(
        update={"APP_VERSION": read_version()},
    )


settings = get_settings()


def reset_settings_cache() -> None:
    """
    清除 Settings 单例缓存。

    修改 .env 后若未重启进程，可主动调用。
    """

    get_settings.cache_clear()
    global settings
    settings = get_settings()

    from app.embedding.factory import reset_embedding_provider_cache
    from app.vectorstore.manager import reset_vector_store_cache

    reset_embedding_provider_cache()
    reset_vector_store_cache()

    from app.rag.pipeline import reset_rag_pipeline_cache

    reset_rag_pipeline_cache()
