"""OpenAPI 元数据与导出（Task 4.8）。"""

from __future__ import annotations

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "存活探针与基础信息。",
    },
    {
        "name": "Monitoring",
        "description": "Prometheus 指标（Task 4.5）。",
    },
    {
        "name": "Chat",
        "description": "对话 Agent API，经 ChatService → AgentRuntime。",
    },
    {
        "name": "Knowledge Assistant",
        "description": "企业知识库上传与 RAG 问答（Task 3.8）。",
    },
    {
        "name": "Dashboard",
        "description": "Software Team Dashboard 后端 API。",
    },
    {
        "name": "Agent Studio",
        "description": "Agent 开发调试：Workflow / Prompt / Memory / Trace（Task 6.8）。",
    },
    {
        "name": "AI Infra Dashboard",
        "description": "模型 / GPU / 缓存 / Agent 基础设施监控（Task 7.8）。",
    },
]


def get_api_description() -> str:

    return (
        "Enterprise LLM Application Platform — 企业级 Agent 与知识助手 REST API。\n\n"
        "- **Swagger UI**: `/docs`\n"
        "- **ReDoc**: `/redoc`\n"
        "- **OpenAPI JSON**: `/openapi.json`\n\n"
        "详细说明见仓库 `docs/API.md`。"
    )
