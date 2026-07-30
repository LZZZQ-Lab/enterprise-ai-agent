# 生产级部署（Task 4.7）

企业环境一键启动：**Nginx**、**API**、**Agent Worker**、**vLLM**、**Chroma（Vector DB）**、**Redis**。

## 架构

```text
                    ┌─────────────┐
  Client ──────────►│   nginx:80  │ (host :8080)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  api :8001  │  FastAPI + Agent Runtime
                    └──┬───┬───┬──┘
           ┌───────────┘   │   └───────────┐
           ▼               ▼               ▼
      ┌─────────┐    ┌─────────┐    ┌─────────┐
      │  vllm   │    │ chroma  │    │  redis  │
      │  :8000  │    │ Vector  │    │  cache  │
      └─────────┘    └─────────┘    └────┬────┘
                                           │
                                    ┌──────▼──────┐
                                    │    agent    │  Worker 心跳 / 队列预留
                                    │   worker    │
                                    └─────────────┘
```

| 服务 | Compose 名 | 说明 |
|------|------------|------|
| **API** | `api` | 对外业务入口（经 Nginx），内网连 vLLM / Chroma / Redis |
| **Agent** | `agent` | 独立 Worker 容器，Redis 就绪探针（可扩展异步任务） |
| **vLLM** | `vllm` | GPU 推理，OpenAI Compatible API |
| **Vector DB** | `chroma` | Chroma Server，持久化 volume `chroma-data` |
| **Redis** | `redis` | 会话/队列基础设施 |
| **Nginx** | `nginx` | 反向代理、超时与大文件上传 |

> **说明**：Agent 推理主路径仍在 **API 进程**内同步执行（`AgentRuntime`）；**agent** 服务用于企业化拆分与后续水平扩展，与 Task 4.5/4.6 监控日志兼容。

## 目录

```text
deploy/
  Dockerfile
  docker-compose.yml
  nginx.conf
  env.example
```

旧版两服务栈（仅 backend + llm）仍保留在 `docker/`，见 [deployment.md](./deployment.md)。

Kubernetes 企业部署（Task 7.7）见 [../deploy/k8s/README.md](../deploy/k8s/README.md)。

## 前置条件

- Docker Engine **24+** / Docker Compose v2
- **NVIDIA GPU** + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- 建议：GPU ≥ 4GB 显存，磁盘 ≥ 10GB，内存 ≥ 8GB

验证 GPU：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## 快速启动

在 **仓库根目录**：

```bash
docker compose -f deploy/docker-compose.yml up --build
```

或：

```bash
cd deploy
cp env.example .env   # 可选
docker compose up --build
```

首次启动 **vllm** 会下载模型（约 1GB）到 volume `hf-cache`，健康检查 `start_period` 最长约 10 分钟。

### 后台运行

```bash
docker compose -f deploy/docker-compose.yml up --build -d
docker compose -f deploy/docker-compose.yml logs -f vllm api nginx
```

### 停止与清理

```bash
docker compose -f deploy/docker-compose.yml down
# 含数据卷：docker compose -f deploy/docker-compose.yml down -v
```

## 验证

默认 Nginx 映射 **`http://localhost:8080`**（`NGINX_HOST_PORT`）。

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/docs
curl http://127.0.0.1:8080/metrics
```

内网 vLLM（不经过 Nginx，需 `docker exec` 或临时暴露端口）：

```bash
docker compose -f deploy/docker-compose.yml exec vllm curl -s http://127.0.0.1:8000/health
```

Redis / Agent Worker：

```bash
docker compose -f deploy/docker-compose.yml exec redis redis-cli ping
docker compose -f deploy/docker-compose.yml exec redis redis-cli get agent:worker:ready
```

## 环境变量

复制 `deploy/env.example` → `deploy/.env`。关键项：

| 变量 | 默认 | 说明 |
|------|------|------|
| `NGINX_HOST_PORT` | 8080 | 对外 HTTP 端口 |
| `VLLM_MODEL` | Qwen2.5-0.5B | vLLM 模型 |
| `VLLM_MAX_LEN` | 512 | 上下文长度 |
| `MODEL_PROVIDER` | vllm | API 使用的 LLM 后端 |
| `EMBEDDING_PROVIDER` | fake | 生产可改为 `openai` / `local` |
| `ENABLE_AGENT_TRACE` | false | 开启 Agent 链路 JSON 日志 |

API 容器内已固定：

- `VLLM_ENDPOINT=http://vllm:8000/v1`
- `CHROMA_HOST=chroma`
- `REDIS_URL=redis://redis:6379/0`
- `VECTOR_STORE_PROVIDER=chroma`

## 数据卷

| Volume | 用途 |
|--------|------|
| `hf-cache` | HuggingFace 模型缓存 |
| `chroma-data` | 向量库持久化 |
| `redis-data` | Redis AOF |
| `api-data` | 知识库上传、Trace 导出目录 |

## 运维建议

1. **TLS**：在生产前置企业网关或 LB 终止 HTTPS，Nginx 仅监听内网。
2. **监控**：Prometheus 抓取 `http://api:8001/metrics`（Docker 内网）或经 Nginx `/metrics`。
3. **vLLM 调优**：见 [vllm_performance_tuning.md](./vllm_performance_tuning.md)，将 `VLLM_GPU_UTIL`、`VLLM_MAX_NUM_SEQS` 写入 `.env`。
4. **无 GPU 开发**：继续使用 `docker/docker-compose.yml` 仅 API，或 `MODEL_PROVIDER=openai` 本地 `.env`（不启动 vllm 需自定义 compose override）。

## 与 Phase 4 其他 Task

| Task | 生产栈中的体现 |
|------|----------------|
| 4.4 vLLM 调优 | compose `command` 支持 batch / GPU 参数 |
| 4.5 监控 | `/metrics` 经 Nginx 暴露 |
| 4.6 链路日志 | `ENABLE_AGENT_TRACE` + `api-data` 卷 |
