# 项目目录结构

Enterprise AI Platform 采用 **Canonical 模块路径 + Legacy 兼容层** 的渐进式迁移策略：新代码优先使用顶层包（`core/`、`llm/`、`knowledge/`、`apps/`），实现仍位于 `backend/app/`，`app.*` 导入继续有效。

## 顶层目录

```text
enterprise-ai-agent/
├── apps/                    # 应用入口（API、Dashboard facade）
│   ├── api/
│   └── dashboard/
├── core/                    # Agent / Workflow / Memory / Tools
├── llm/                     # Provider / Router / Gateway
├── knowledge/               # RAG / Embedding / VectorStore
├── infra/                   # 部署与监控（统一基础设施目录）
│   ├── docker/              # 开发 / 轻量 Compose + Dockerfile
│   ├── deploy/              # 生产 Compose（Nginx 全栈）
│   ├── k8s/                 # Kubernetes 清单
│   └── monitoring/          # Prometheus 指标 facade
├── backend/                 # Python 运行时根目录
│   ├── app/                 # Legacy 实现包（与 canonical 等价）
│   ├── applications/        # 业务应用（Software Team 等）
│   ├── benchmark/ · loadtest/ · security/ · observability/
│   ├── artifacts/           # 测试 / 压测 / Benchmark 报告输出
│   └── scripts/
├── tests/                   # pytest（unit / integration / e2e）
├── examples/                # 独立 Demo 脚本
├── docs/                    # 架构、部署与开发文档
├── frontend/                # Vue Dashboard
├── deploy/                  # 兼容入口（→ infra/deploy）
└── docker/                  # 兼容入口（→ infra/docker）
```

## 已移除的冗余顶层目录

| 原路径 | 迁移至 |
|--------|--------|
| `benchmark/`（薄包装脚本） | 直接在 `backend/` 下运行 `python -m benchmark.*` |
| `dashboard/`（仅 README） | [docs/infra_dashboard.md](./infra_dashboard.md) |
| `artifacts/`（重复报告） | `backend/artifacts/` |
| `DEMO.md` | [docs/demos/library_system.md](./demos/library_system.md) |

## Canonical ↔ Legacy 映射

| Canonical 导入 | Legacy 导入 | 实现位置 |
|----------------|-------------|----------|
| `from apps.api import app` | `from app.main import app` | `backend/app/main.py` |
| `from core.agent import ChatAgent` | `from app.agents import ChatAgent` | `backend/app/agents/` |
| `from core.workflow import WorkflowExecutor` | `from app.workflow import WorkflowExecutor` | `backend/app/workflow/` |
| `from core.memory import EnterpriseMemoryManager` | `from app.memory import ...` | `backend/app/memory/` |
| `from core.tools import ToolManager` | `from app.tools import ToolManager` | `backend/app/tools/` |
| `from llm.providers import get_llm_client` | `from app.llm import get_llm_client` | `backend/app/llm/` |
| `from llm.router import RouterEngine` | `from app.router import RouterEngine` | `backend/app/router/` |
| `from llm.gateway import InferenceGateway` | `from app.gateway import InferenceGateway` | `backend/app/gateway/` |
| `from knowledge.rag import RAGPipeline` | `from app.rag import RAGPipeline` | `backend/app/rag/` |
| `from knowledge.embedding import get_embedding_provider` | `from app.embedding import ...` | `backend/app/embedding/` |
| `from knowledge.vectorstore import get_vector_store` | `from app.vectorstore import ...` | `backend/app/vectorstore/` |
| `from infra.monitoring import infra_metrics` | `from app.monitoring import ...` | `backend/app/monitoring/` |

## 部署路径

| 场景 | 推荐路径 | 兼容路径 |
|------|----------|----------|
| 轻量 API / 开发栈 | `infra/docker/docker-compose*.yml` | `docker/docker-compose*.yml` |
| 生产全栈 | `infra/deploy/docker-compose.yml` | `deploy/docker-compose.yml` |
| Kubernetes | `infra/k8s/` | — |
| 生产镜像构建 | `infra/deploy/Dockerfile` | — |

## 运行与测试

```bash
# API（兼容）
cd backend && uvicorn app.main:app --port 8001

# API（canonical）
cd backend && uvicorn apps.api:app --port 8001

# 测试
cd backend && pytest -m "not integration"

# Docker 轻量栈
docker compose -f infra/docker/docker-compose.api-only.yml up --build

# Docker 生产栈
docker compose -f infra/deploy/docker-compose.yml up --build
```

## PYTHONPATH

本地开发与 CI 在 `backend/` 下执行时，`pytest.ini` 设置：

```ini
pythonpath = . ..
```

即同时加载 `backend/`（`app` 包）与仓库根目录（`core`、`llm`、`knowledge`、`apps`）。
