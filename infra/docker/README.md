# Task 2.7 Docker Compose（Task 9.1：`infra/docker/`）

## 全栈（API + vLLM，需 NVIDIA GPU）

```bash
# 仓库根目录
docker compose -f infra/docker/docker-compose.yml up --build
```

后端依赖 `llm` 健康检查通过后才会启动；**无 GPU 时 backend 一直起不来**，Swagger 也会打不开。

## 仅 API（Phase 3 Swagger / 知识助手 Demo，无需 GPU）

```bash
docker compose -f infra/docker/docker-compose.api-only.yml up --build
```

- Swagger：**http://localhost:8001/docs**
- 健康检查：**http://localhost:8001/health**

## 兼容旧路径

`docker/docker-compose*.yml` 通过 Compose `include` 转发至本目录，命令可继续使用 `-f docker/...`。

## Swagger 打不开时

| 现象 | 原因 | 处理 |
|------|------|------|
| 8000 无 `/docs` | **8000 是 vLLM**，不是 FastAPI | 用 **http://localhost:8001/docs** |
| `/health` 正常但 `/docs` 一直加载 | Swagger 默认从境外 CDN 拉 JS | 在 `backend/.env` 设 `SWAGGER_UI_CDN=bootcdn` 后重启；或试 **http://localhost:8001/redoc**、直接打开 **/openapi.json** |
| 连接被拒绝 | API 未启动 | `cd backend` 后 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8001` |
| Docker 一直 Waiting | 在等 vLLM GPU | 改用 `docker-compose.api-only.yml` 或本地 uvicorn |
| 生产 nginx | 文档在 API 容器 8001 | `deploy` 栈对外多为 **8080**，需看 nginx 是否转发 `/docs` |

详见 [docs/deployment.md](../../docs/deployment.md)。
