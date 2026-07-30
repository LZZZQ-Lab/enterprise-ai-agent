#!/usr/bin/env python3
"""
Task 5.2 Demo：Product Agent 生成完整 PRD。

用法：
    cd backend
    python -m applications.software_team.run_product_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_REQUIREMENT = "开发一个博客系统，支持文章发布、分类、评论与管理员后台。"


class BlogPRDMockLLM:
    """演示用 LLM：输出含四类章节的完整 PRD。"""

    model = "demo-mock-product"

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        user = messages[-1].content or ""

        if "博客" in user or "blog" in user.lower():

            body = """# 产品需求文档（PRD）— 博客系统

## 功能需求

| 优先级 | 模块 | 功能 | 验收 |
|--------|------|------|------|
| P0 | 文章 | 创建/编辑/发布/下线 Markdown 文章 | 发布后前台可见 |
| P0 | 分类 | 分类 CRUD、文章归属单一分类 | 列表可按分类筛选 |
| P0 | 评论 | 登录用户评论、管理员删评 | 未登录不可评论 |
| P1 | 标签 | 多标签、标签云 | 点击标签过滤文章 |
| P1 | 搜索 | 标题与正文关键词搜索 | 结果分页 |
| P0 | 后台 | 仪表盘、用户管理、内容审核 | 仅 admin 可访问 |

## 用户角色

- **访客**：浏览已发布文章与分类
- **作者**：管理自己的文章草稿与发布
- **管理员**：全站内容、用户、评论与系统配置

## 业务流程

1. 访客浏览文章列表与详情
2. 用户注册/登录后可发表评论
3. 作者创建草稿 → 预览 → 发布
4. 管理员在后台审核评论、管理用户与分类
5. 下线或删除违规内容并记录审计日志

## API 需求

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/posts | 文章列表 `?category=&tag=&q=` |
| POST | /api/v1/posts | 创建文章（author+） |
| GET | /api/v1/posts/{id} | 文章详情 |
| PUT | /api/v1/posts/{id} | 更新文章 |
| DELETE | /api/v1/posts/{id} | 删除文章 |
| GET | /api/v1/categories | 分类列表 |
| POST | /api/v1/posts/{id}/comments | 发表评论 |
| GET | /api/v1/admin/users | 用户列表（admin） |

## 非功能需求

- 性能：列表页 P95 < 300ms
- 安全：评论 XSS 过滤、CSRF、RBAC
"""

            return ChatResult(model=self.model, content=body)

        return ChatResult(
            model=self.model,
            content="# PRD\n\n## 功能需求\n\nTBD\n\n## 用户角色\n\nTBD\n\n## 业务流程\n\nTBD\n\n## API需求\n\nTBD\n",
        )


class MockEnterpriseRetriever:
    """演示 RAG：返回企业 API 规范片段。"""

    def retrieve(self, query, top_k=3, score_threshold=0.0):
        from app.rag.types import Document
        from app.rag.types import ScoredDocument

        doc = Document(
            id="std-api-1",
            content=(
                "【企业 API 规范】所有对外 REST 接口必须使用 /api/v1 前缀；"
                "统一错误体 code/message；分页参数 page、page_size；"
                "敏感操作需审计日志。"
            ),
            metadata={"source": "enterprise-standards/api.md"},
        )

        return [ScoredDocument(document=doc, score=0.92)]


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Product Requirement Agent Demo (Task 5.2)",
    )

    parser.add_argument(
        "--requirement",
        default=DEFAULT_REQUIREMENT,
    )

    parser.add_argument(
        "--no-rag",
        action="store_true",
    )

    args = parser.parse_args()

    from app.agents.software_team.product_agent import ProductRequirementAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    config = AgentConfig(
        max_iterations=1,
        enable_mcp=False,
        enable_rag=not args.no_rag,
        enable_trace=False,
        top_k=3,
    )

    agent = ProductRequirementAgent(
        config=config,
        client=BlogPRDMockLLM(),
        retriever=None if args.no_rag else MockEnterpriseRetriever(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-product-prd",
            user_message=args.requirement,
            agent_name="product",
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
