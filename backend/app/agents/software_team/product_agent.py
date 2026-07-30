"""
Phase 5.2：Product Requirement Agent — 模拟产品经理，输出完整 PRD。
"""

from __future__ import annotations

import re
from typing import Any
from typing import Protocol

from app.agents.base import BaseAgent
from app.agents.software_team.prd_prompt import fetch_enterprise_standards
from app.agents.software_team.prd_prompt import render_prd_template
from app.agents.types import AgentContext
from app.agents.types import AgentResult
from app.config import AgentConfig


class PRDGenerationClient(Protocol):
    model: str

    def chat(self, messages, use_tools: bool = True): ...


REQUIRED_PRD_SECTIONS = (
    "功能需求",
    "用户角色",
    "业务流程",
    "API需求",
)


class ProductRequirementAgent(BaseAgent):
    """
    输入用户需求 →（可选 RAG 企业规范）→ Prompt 模板 → LLM → 完整 PRD。
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: PRDGenerationClient | None = None,
        retriever: Any | None = None,
    ) -> None:

        super().__init__()

        self._config = config or AgentConfig.from_env()
        self._client = client
        self._retriever = retriever

        self.last_prd: str = ""
        self.last_rag_hits: list[Any] = []

    @property
    def name(self) -> str:

        return "product"

    def get_capabilities(self) -> list[str]:

        caps = [
            "software_team",
            "prd",
            "requirements",
        ]

        if self._config.enable_rag:

            caps.append("rag")

        return caps

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:

        requirement = self._resolve_requirement(context)

        if not requirement:

            return AgentResult(
                success=False,
                model="product",
                content="Empty user requirement.",
            )

        goal_summary = str(
            context.shared_context.get("goal_summary")
            or context.metadata.get("goal_summary")
            or ""
        )

        project_name = str(
            context.shared_context.get("project_name")
            or context.metadata.get("project_name")
            or ""
        )

        standards, hits = fetch_enterprise_standards(
            requirement,
            config=self._config,
            retriever=self._retriever,
        )

        self.last_rag_hits = hits

        user_prompt = render_prd_template(
            user_requirement=requirement,
            project_name=project_name,
            goal_summary=goal_summary,
            enterprise_standards=standards,
        )

        if self._client is None:

            prd = self._fallback_prd(
                requirement=requirement,
                project_name=project_name or requirement[:48],
                enterprise_snippet=standards[:500] if standards else "",
            )

            self.last_prd = prd

            return AgentResult(
                success=True,
                model="template_fallback",
                content=prd,
            )

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

        prd = (result.content or "").strip()

        if not prd or not _has_required_sections(prd):

            prd = self._fallback_prd(
                requirement=requirement,
                project_name=project_name or requirement[:48],
                enterprise_snippet=standards[:500] if standards else "",
            )

            model = "template_fallback"

        else:

            model = getattr(result, "model", "product")

        self.last_prd = prd

        return AgentResult(
            success=True,
            model=model,
            content=prd,
        )

    @staticmethod
    def _resolve_requirement(context: AgentContext) -> str:

        if context.metadata.get("requirement"):

            return str(context.metadata["requirement"]).strip()

        return context.user_message.strip()

    @staticmethod
    def _fallback_prd(
        *,
        requirement: str,
        project_name: str,
        enterprise_snippet: str,
    ) -> str:

        compliance = ""

        if enterprise_snippet:

            compliance = (
                "\n## 合规说明\n"
                "已参考企业规范片段（RAG）：\n"
                f"{enterprise_snippet[:800]}\n"
            )

        return f"""# 产品需求文档（PRD）

**项目**：{project_name}

## 1. 功能需求

### 1.1 核心功能（P0）

| 模块 | 功能 | 验收要点 |
|------|------|----------|
| 内容 | 与用户诉求「{requirement[:80]}」直接相关的 CRUD 与展示 | 主流程可演示 |
| 账户 | 注册/登录、会话与基础权限 | 未授权不可访问受保护资源 |
| 管理 | 后台配置与审计日志 | 关键操作可追溯 |

### 1.2 扩展功能（P1）

- 搜索与筛选
- 导入导出
- 通知（邮件/站内）

## 2. 用户角色

| 角色 | 职责 | 权限 |
|------|------|------|
| 访客 | 浏览公开内容 | 只读 |
| 注册用户 | 使用核心业务功能 | 读写本人数据 |
| 管理员 | 用户与系统配置 | 全局管理 |

## 3. 业务流程

1. 用户注册或登录系统
2. 根据角色进入对应工作台
3. 执行核心业务操作（创建/编辑/提交/审核）
4. 系统持久化数据并返回结果
5. 管理员在后台查看统计与日志

## 4. API 需求

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 登录，返回 token |
| POST | /api/v1/auth/register | 注册 |
| GET | /api/v1/resources | 资源列表（分页、筛选） |
| POST | /api/v1/resources | 创建资源 |
| GET | /api/v1/resources/{{id}} | 资源详情 |
| PUT | /api/v1/resources/{{id}} | 更新资源 |
| DELETE | /api/v1/resources/{{id}} | 删除资源 |
| GET | /api/v1/admin/metrics | 管理端统计（需 admin） |

### 4.1 通用约定

- 认证：`Authorization: Bearer <token>`
- 错误：`{{"code","message","details"}}`
- 分页：`page`, `page_size`, `total`

## 5. 非功能需求

- 性能：常规 API P95 < 500ms（单机演示环境可放宽）
- 安全：HTTPS、输入校验、防 XSS/CSRF
- 可观测：结构化日志与请求 ID

{compliance}
---
*Generated by ProductRequirementAgent (fallback)*
"""


def _has_required_sections(prd: str) -> bool:

    compact = re.sub(r"\s+", "", prd)

    for section in REQUIRED_PRD_SECTIONS:

        if section in prd or section in compact:

            continue

        if section == "API需求" and (
            "API 需求" in prd or "接口需求" in prd
        ):

            continue

        return False

    return True
