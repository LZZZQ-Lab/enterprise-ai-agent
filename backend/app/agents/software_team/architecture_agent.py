"""
Phase 5.3：Architecture Agent — 模拟架构师，输出 architecture.md。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.software_team.architecture_prompt import (
    ARCHITECTURE_ARTIFACT_FILENAME,
)
from app.agents.software_team.architecture_prompt import (
    fetch_architecture_knowledge,
)
from app.agents.software_team.architecture_prompt import (
    render_architecture_template,
)
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class ArchitectureGenerationClient(Protocol):
    model: str

    def chat(self, messages, use_tools: bool = True): ...


REQUIRED_DESIGN_SECTIONS = (
    "系统架构",
    "技术选型",
    "数据库设计",
    "接口设计",
)


class ArchitectureAgent(BaseAgent):
    """
    输入 PRD → Knowledge RAG → Prompt 模板 → LLM → System Design（architecture.md）。
    """

    ARTIFACT_RELATIVE_PATH = f"docs/{ARCHITECTURE_ARTIFACT_FILENAME}"

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: ArchitectureGenerationClient | None = None,
        retriever: Any | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client
        self._retriever = retriever

        self.last_document: str = ""
        self.last_artifact_path: str | None = None
        self.last_rag_hits: list[Any] = []

    @property
    def name(self) -> str:

        return "architecture"

    def get_capabilities(self) -> list[str]:

        caps = [
            "software_team",
            "system_design",
            "architecture",
        ]

        if self._config.enable_rag:

            caps.append("rag")

        return caps

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        prd = self._resolve_prd(context)

        if not prd:

            return AgentResult(
                success=False,
                model="architecture",
                content="Empty PRD input.",
            )

        project_name = str(
            context.shared_context.get("project_name")
            or context.metadata.get("project_name")
            or ""
        )

        goal_summary = str(
            context.shared_context.get("goal_summary")
            or context.metadata.get("goal_summary")
            or ""
        )

        knowledge, hits = fetch_architecture_knowledge(
            prd,
            config=self._config,
            retriever=self._retriever,
        )

        self.last_rag_hits = hits

        user_prompt = render_architecture_template(
            prd_content=prd,
            project_name=project_name,
            goal_summary=goal_summary,
            knowledge_context=knowledge,
        )

        if self._client is None:

            document = self._fallback_architecture(
                prd=prd,
                project_name=project_name or "System",
                knowledge_snippet=knowledge[:600] if knowledge else "",
            )

            model = "template_fallback"

        else:

            from app.llm.types import Message

            result = self._client.chat(
                [
                    Message(
                        role="user",
                        content=user_prompt,
                    ),
                ],
                use_tools=False,
            )

            document = (result.content or "").strip()

            if not document or not _has_required_sections(document):

                document = self._fallback_architecture(
                    prd=prd,
                    project_name=project_name or "System",
                    knowledge_snippet=knowledge[:600] if knowledge else "",
                )

                model = "template_fallback"

            else:

                model = getattr(result, "model", "architecture")

        document = _ensure_architecture_title(document)

        self.last_document = document

        artifact_path = self._maybe_write_artifact(
            context,
            document,
        )

        self.last_artifact_path = artifact_path

        prefix = ""

        if artifact_path:

            prefix = f"architecture.md 已写入：`{artifact_path}`\n\n"

        return AgentResult(
            success=True,
            model=model,
            content=prefix + document,
        )

    def _maybe_write_artifact(
        self,
        context: AgentContext,
        document: str,
    ) -> str | None:

        artifact_dir = context.metadata.get("artifact_dir")

        if not artifact_dir:

            return None

        root = Path(str(artifact_dir))

        target = root / self.ARTIFACT_RELATIVE_PATH

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document, encoding="utf-8")

        return str(target.resolve())

    @staticmethod
    def _resolve_prd(context: AgentContext) -> str:

        for key in ("prd", "PRD"):

            if context.metadata.get(key):

                return str(context.metadata[key]).strip()

            if context.shared_context.get(key):

                return str(context.shared_context[key]).strip()

        if context.metadata.get("prd_content"):

            return str(context.metadata["prd_content"]).strip()

        return context.user_message.strip()

    @staticmethod
    def _fallback_architecture(
        *,
        prd: str,
        project_name: str,
        knowledge_snippet: str,
    ) -> str:

        adr = ""

        if knowledge_snippet:

            adr = (
                "\n## 架构决策记录（ADR）\n"
                "已参考知识库片段：\n"
                f"{knowledge_snippet}\n"
            )

        prd_hint = prd.strip()[:400].replace("\n", " ")

        return f"""# System Design — {project_name}

> 文档：`architecture.md`  
> 依据 PRD 摘要：{prd_hint}…

## 系统架构

```mermaid
flowchart TB
  subgraph Client
    Web[Web / Admin UI]
  end
  subgraph App
    API[API Service]
    Auth[Auth Module]
  end
  subgraph Data
    DB[(PostgreSQL)]
    Cache[(Redis)]
  end
  Web --> API
  API --> Auth
  API --> DB
  API --> Cache
```

- **分层**：表现层（Web）→ 应用层（REST API）→ 数据层（PostgreSQL + Redis）
- **边界**：认证、业务、管理后台通过 API 统一暴露

## 技术选型

| 层次 | 选型 | 理由 |
|------|------|------|
| 后端 | Python 3.11 + FastAPI | 与平台 Agent Runtime 一致，异步友好 |
| 前端 | React / Vue（二选一） | 组件化、生态成熟 |
| 数据库 | PostgreSQL | 关系型、JSON 扩展、事务 |
| 缓存 | Redis | 会话、热点读 |
| 部署 | Docker Compose → K8s | 本地演示与生产可演进 |

## 数据库设计

| 表 | 主要字段 | 说明 |
|----|----------|------|
| users | id, email, password_hash, role, created_at | 用户与角色 |
| resources | id, owner_id, title, body, status, created_at | 核心业务实体（随 PRD 映射） |
| categories | id, name, slug | 分类 |
| comments | id, resource_id, user_id, content, created_at | 评论 |
| audit_logs | id, actor_id, action, payload, created_at | 审计 |

- 索引：`resources(status, created_at)`、`comments(resource_id)`
- 外键：`resources.owner_id → users.id`

## 接口设计

- **风格**：REST `/api/v1`，JSON  body，JWT Bearer 鉴权
- **对齐 PRD**：登录/注册、资源 CRUD、分类、评论、管理端指标
- **错误**：`{{"code": "...", "message": "...", "details": {{}}}}`
- **分页**：`page`, `page_size`, 响应含 `total`

### 核心接口（示例）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/resources | 列表 |
| POST | /api/v1/resources | 创建 |
| GET | /api/v1/resources/{{id}} | 详情 |

## 非功能架构

- **安全**：RBAC、HTTPS、参数校验、审计日志
- **可观测**：结构化日志、请求 ID、健康检查 `/health`

{adr}
---
*Generated by ArchitectureAgent (fallback)*
"""


def _has_required_sections(document: str) -> bool:

    compact = re.sub(r"\s+", "", document)

    for section in REQUIRED_DESIGN_SECTIONS:

        if section in document or section in compact:

            continue

        return False

    return True


def _ensure_architecture_title(document: str) -> str:

    stripped = document.lstrip()

    if stripped.startswith("#"):

        return document

    return f"# System Design\n\n{document}"
