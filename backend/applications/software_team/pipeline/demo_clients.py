"""
Task 5.8：完整团队 Demo 的 Mock LLM（用户管理系统场景）。
"""

from __future__ import annotations

import json


class UserManagementPMMockLLM:
    model = "demo-pm-user-mgmt"

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        user = messages[-1].content or ""

        if "SOFTWARE_TEAM_TASK_PLAN_GOAL" in user:

            return ChatResult(
                model=self.model,
                content=(
                    "交付可部署的用户管理系统 MVP：用户 CRUD、角色权限、"
                    "登录鉴权与管理员后台。"
                ),
            )

        if "SOFTWARE_TEAM_TASK_PLAN" in user:

            tasks = [
                {
                    "title": "用户管理系统 PRD",
                    "description": "用户故事、角色、API 与验收标准",
                    "agent": "product",
                },
                {
                    "title": "架构设计",
                    "description": "模块、数据库、API、部署视图",
                    "agent": "architecture",
                },
                {
                    "title": "后端与 API 实现",
                    "description": "用户/角色/鉴权核心代码",
                    "agent": "developer",
                },
                {
                    "title": "代码审查",
                    "description": "安全与规范审查",
                    "agent": "reviewer",
                },
                {
                    "title": "自动化测试",
                    "description": "单元测试与 API 测试",
                    "agent": "tester",
                },
                {
                    "title": "容器化部署",
                    "description": "Dockerfile 与 compose",
                    "agent": "devops",
                },
            ]

            return ChatResult(
                model=self.model,
                content=json.dumps(tasks, ensure_ascii=False),
            )

        return ChatResult(model=self.model, content="[]")


class UserManagementProductMockLLM:
    model = "demo-product-user-mgmt"

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        body = """# 产品需求文档（PRD）— 用户管理系统

## 功能需求

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 用户 CRUD | 创建/查询/更新/禁用用户 |
| P0 | 角色与权限 | admin / user 角色，RBAC |
| P0 | 登录鉴权 | JWT 登录、会话失效 |
| P1 | 审计日志 | 关键操作记录 |

## 用户角色

- **管理员**：用户与角色管理、系统配置
- **普通用户**：查看与编辑本人资料

## 业务流程

1. 管理员创建用户并分配角色
2. 用户登录获取 token
3. 访问受保护 API 时校验角色
4. 管理员可禁用用户

## API 需求

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/users | 用户列表（admin） |
| POST | /api/v1/users | 创建用户 |
| GET | /api/v1/users/{id} | 用户详情 |
| PUT | /api/v1/users/{id} | 更新用户 |
| DELETE | /api/v1/users/{id} | 删除/禁用 |

## 非功能需求

- 密码哈希存储，禁止明文
- API P95 < 500ms（演示环境）
"""

        return ChatResult(model=self.model, content=body)


class UserManagementArchitectureMockLLM:
    model = "demo-arch-user-mgmt"

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        body = """# System Design — 用户管理系统

## 系统架构

- FastAPI 单体 + PostgreSQL + Redis（session 可选）
- 模块：auth、users、roles、admin

```mermaid
flowchart LR
  Client --> API
  API --> DB[(PostgreSQL)]
```

## 技术选型

| 组件 | 选型 |
|------|------|
| API | FastAPI |
| ORM | SQLAlchemy |
| DB | PostgreSQL 15 |

## 数据库设计

- **users**(id, email, password_hash, role, is_active, created_at)
- **audit_logs**(id, actor_id, action, created_at)

## 接口设计

REST `/api/v1`，JWT Bearer，统一错误体与分页。
"""

        return ChatResult(model=self.model, content=body)
