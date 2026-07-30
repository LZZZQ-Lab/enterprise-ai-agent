# deploy/ — 生产 Compose 栈（Task 4.7）

完整文档：[docs/production_deploy.md](../docs/production_deploy.md)

```bash
# 仓库根目录
docker compose -f deploy/docker-compose.yml up --build

# 或
cd deploy && docker compose up --build
```

服务：`nginx` · `api` · `agent` · `vllm` · `chroma` · `redis`

**Kubernetes（Task 7.7）**：见 [infra/k8s/README.md](../infra/k8s/README.md)（Deployment / Service / Ingress / ConfigMap / Secret / HPA）。

轻量开发栈（仅 API + vLLM）见 [../infra/docker/README.md](../infra/docker/README.md).
