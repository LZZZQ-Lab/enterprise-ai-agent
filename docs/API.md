# REST API 文档（Task 4.8）

| 类型 | URL |
|------|-----|
| Swagger UI | `/docs` |
| ReDoc | `/redoc` |
| OpenAPI JSON | `/openapi.json` |

```bash
cd backend && python scripts/export_openapi.py
```

## 端点摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/metrics` | Prometheus |
| POST | `/api/v1/chat` | 对话 Agent |
| POST | `/api/v1/knowledge/documents` | 上传知识库 |
| POST | `/api/v1/knowledge/ask` | 知识问答 |

Dashboard 路由见 Swagger **Dashboard** 标签。版本见 [VERSION](../VERSION)。
