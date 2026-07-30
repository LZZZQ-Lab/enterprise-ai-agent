# Docker 兼容入口（Task 9.1）

Compose 与 Dockerfile 已迁移至 **[../infra/docker/](../infra/docker/)**。

```bash
# 推荐（新路径）
docker compose -f infra/docker/docker-compose.yml up --build
docker compose -f infra/docker/docker-compose.api-only.yml up --build

# 兼容（旧路径，等价于上述 include）
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.api-only.yml up --build
```

详见 [infra/docker/README.md](../infra/docker/README.md)。
