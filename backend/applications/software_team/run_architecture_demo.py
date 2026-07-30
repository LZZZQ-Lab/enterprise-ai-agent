#!/usr/bin/env python3
"""
Task 5.3 Demo：Architecture Agent 根据 PRD 生成 architecture.md。

用法：
    cd backend
    python -m applications.software_team.run_architecture_demo
    python -m applications.software_team.run_architecture_demo --write ./tmp-demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


SAMPLE_BLOG_PRD = """# 产品需求文档（PRD）— 博客系统

## 功能需求

- P0：文章 CRUD、Markdown、发布/下线
- P0：分类、评论、管理后台
- P1：标签、搜索

## 用户角色

访客、作者、管理员

## 业务流程

浏览 → 登录 → 创作/评论 → 后台审核

## API 需求

POST /api/v1/auth/login；GET/POST /api/v1/posts；评论与分类 API
"""


class BlogArchitectureMockLLM:
    model = "demo-mock-architecture"

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        body = """# System Design — 博客系统

## 系统架构

- 单体 FastAPI 应用 + 静态前端，Docker Compose 部署
- 模块：auth、posts、categories、comments、admin

```mermaid
flowchart LR
  Browser --> Nginx --> API
  API --> PostgreSQL
  API --> Redis
```

## 技术选型

| 组件 | 选型 |
|------|------|
| API | FastAPI + SQLAlchemy |
| DB | PostgreSQL 15 |
| Cache | Redis（session） |
| UI | React SPA |

## 数据库设计

- **users**(id, email, role)
- **posts**(id, author_id, category_id, title, body_md, status)
- **categories**(id, name, slug)
- **comments**(id, post_id, user_id, content)

## 接口设计

REST `/api/v1`：auth、posts、categories、comments；JWT；统一错误体与分页。

## 架构决策记录（ADR）

采用单体优先，满足 MVP 可部署。
"""

        return ChatResult(model=self.model, content=body)


class MockArchitectureKnowledgeRetriever:
    def retrieve(self, query, top_k=3, score_threshold=0.0):
        from app.rag.types import Document
        from app.rag.types import ScoredDocument

        doc = Document(
            id="arch-std-1",
            content=(
                "【企业架构规范】新服务默认 PostgreSQL；"
                "对外 API 必须 /api/v1；核心表需 updated_at 与软删字段可选。"
            ),
            metadata={"source": "knowledge/architecture-standards.md"},
        )

        return [ScoredDocument(document=doc, score=0.88)]


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Architecture Agent Demo (Task 5.3)",
    )

    parser.add_argument(
        "--write",
        default="",
        help="若指定目录，将写入 docs/architecture.md",
    )

    args = parser.parse_args()

    from app.agents.software_team.architecture_agent import ArchitectureAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    config = AgentConfig(
        max_iterations=1,
        enable_mcp=False,
        enable_rag=True,
        enable_trace=False,
    )

    metadata = {}

    if args.write:

        metadata["artifact_dir"] = args.write

    agent = ArchitectureAgent(
        config=config,
        client=BlogArchitectureMockLLM(),
        retriever=MockArchitectureKnowledgeRetriever(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-architecture",
            user_message=SAMPLE_BLOG_PRD,
            agent_name="architecture",
            metadata=metadata,
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
