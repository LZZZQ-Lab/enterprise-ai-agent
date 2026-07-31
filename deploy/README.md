# deploy/ — 兼容入口

生产 Compose 栈已迁移至 **[infra/deploy/](../infra/deploy/)**。

```bash
# 推荐（canonical）
docker compose -f infra/deploy/docker-compose.yml up --build

# 兼容旧命令
docker compose -f deploy/docker-compose.yml up --build
```

完整文档：[docs/production_deploy.md](../docs/production_deploy.md)
