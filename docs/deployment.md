# 企业部署指南（Task 2.7 / 4.7）

> **生产全栈（推荐企业环境）**：Nginx + API + Agent Worker + vLLM + Chroma + Redis → **[production_deploy.md](./production_deploy.md)**，`infra/deploy/docker-compose.yml`。

本文说明使用 **Docker Compose** 同时启动（**轻量栈 `docker/`**）：

| 服务 | 容器名 | 默认端口 | 说明 |
|------|--------|----------|------|
| **backend** | `enterprise-ai-backend` | 8001 | FastAPI Platform API |
| **llm** | `enterprise-ai-llm` | 8000 | vLLM OpenAI Compatible API |

架构关系：

```text
Client → http://localhost:8001  (backend)
              → VLLM_ENDPOINT=http://llm:8000/v1  (Docker 内网)
              → vLLM → GPU
```

本地 WSL 脚本部署见 [vllm_deployment.md](vllm_deployment.md)；Docker 方案适用于 **Linux 服务器 / 带 GPU 的 Docker Desktop**。

---

## 1. 前置条件

### 1.1 软件

- Docker Engine **24+** 或 Docker Desktop
- Docker Compose v2（`docker compose` 子命令）
- **NVIDIA GPU** + 驱动
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)（Linux）或 Docker Desktop 开启 **WSL2 + GPU**

验证 GPU 可见：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### 1.2 资源建议

| 项目 | 建议 |
|------|------|
| GPU 显存 | ≥ 4 GB（Qwen2.5-0.5B，默认 `max-model-len=512`） |
| 磁盘 | ≥ 5 GB（镜像 + HuggingFace 权重 volume） |
| 内存 | ≥ 8 GB |

---

## 2. 目录与文件

```text
docker/
  Dockerfile           # backend 镜像
  docker-compose.yml   # backend + llm
  env.example          # 可选环境变量模板
docs/
  deployment.md        # 本文档
```

---

## 3. 快速启动

在 **仓库根目录** 执行：

```bash
docker compose -f docker/docker-compose.yml up --build
```

首次启动 **llm** 会拉取镜像并下载模型（约 1GB），`llm` 健康检查 `start_period` 最长约 10 分钟，请耐心等待日志出现 ready。

### 3.1 可选：自定义环境变量

```bash
cp docker/env.example docker/.env
# 编辑 docker/.env 后：
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
```

### 3.2 后台运行

```bash
docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml logs -f llm backend
```

---

## 4. 验证

### 4.1 vLLM（llm 服务）

```bash
curl http://127.0.0.1:8000/v1/models
curl http://127.0.0.1:8000/health
```

### 4.2 Platform API（backend 服务）

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/docs
```

### 4.3 对话（经 Platform 走 vLLM）

按项目 Chat API 文档调用 `http://127.0.0.1:8001/api/v1/...`（见 Swagger `/docs`）。

容器内 backend 已默认：

```env
MODEL_PROVIDER=vllm
VLLM_ENDPOINT=http://llm:8000/v1
MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
VLLM_MAX_TOKENS=256
```

---

## 5. 常用运维命令

```bash
# 停止并删除容器（保留 hf-cache  volume）
docker compose -f docker/docker-compose.yml down

# 停止并删除 volume（重新下载模型）
docker compose -f docker/docker-compose.yml down -v

# 仅重建 backend
docker compose -f docker/docker-compose.yml up --build backend

# 查看状态
docker compose -f docker/docker-compose.yml ps
```

---

## 6. 配置说明

| 变量 | 默认 | 作用 |
|------|------|------|
| `VLLM_MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | vLLM 加载的模型 |
| `VLLM_MAX_LEN` | `512` | 最大上下文（小显存） |
| `VLLM_GPU_UTIL` | `0.65` | GPU 显存占用比例 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | 模型下载镜像（可改回官方） |
| `BACKEND_HOST_PORT` | `8001` | 宿主机 API 端口 |
| `LLM_HOST_PORT` | `8000` | 宿主机 vLLM 端口 |
| `MODEL_PROVIDER` | `vllm` | backend 使用的 LLM 后端 |

权重缓存在 Docker volume **`hf-cache`**，重复部署无需重新下载。

---

## 7. 与开发环境差异

| 场景 | 推荐方式 |
|------|----------|
| Windows 本机 + WSL 调试 | [vllm_deployment.md](vllm_deployment.md) 脚本启动 |
| Linux GPU 服务器 / K8s 前验证 | 本文 Docker Compose |
| 仅 API、云端 OpenAI | 可只构建 `backend` 镜像，设 `MODEL_PROVIDER=openai`（需自行改 compose 或单独 `docker run`） |

---

## 8. 故障排查

### Q1: `llm` 一直 unhealthy

- 查看日志：`docker compose -f docker/docker-compose.yml logs llm`
- 显存不足：降低 `VLLM_GPU_UTIL` / `VLLM_MAX_LEN`
- 下载失败：检查网络或 `HF_ENDPOINT`，或预填充 `hf-cache`

### Q2: `backend` 启动报连接 vLLM 失败

- 确认 `llm` 已为 healthy：`docker compose ps`
- 容器内应使用 **`http://llm:8000/v1`**，不要用 `127.0.0.1`

### Q3: Windows 无 GPU / 仅 CPU

- 完整双服务栈 **需要 GPU**；无 GPU 时请用 WSL/云端 OpenAI，或仅本地脚本 [vllm_deployment.md](vllm_deployment.md) 中 `MODEL_PROVIDER=openai`

### Q4: 端口冲突

- 修改 `docker/.env` 中 `BACKEND_HOST_PORT` / `LLM_HOST_PORT`

---

## 9. 相关文档

- [vllm_deployment.md](vllm_deployment.md) — Task 2.4 / 2.5 vLLM 与 Platform 对接
- [performance.md](performance.md) — Task 2.6 性能基准
- [README.md](../README.md) — 项目总览
