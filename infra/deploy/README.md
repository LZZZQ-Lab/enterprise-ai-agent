# infra/deploy/ — 生产 Compose 栈（Task 4.7 / 9.x）

完整文档：[docs/production_deploy.md](../../docs/production_deploy.md)

```bash
# 仓库根目录（推荐）
docker compose -f infra/deploy/docker-compose.yml up --build

# 兼容旧路径
docker compose -f deploy/docker-compose.yml up --build
```

服务：`nginx` · `api` · `agent` · `vllm` · `chroma` · `redis`

**Kubernetes**：见 [infra/k8s/README.md](../k8s/README.md)

**轻量开发栈**（仅 API ± vLLM）：见 [infra/docker/README.md](../docker/README.md)
