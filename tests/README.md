# 测试体系（Task 8.1）

## 目录结构

```text
tests/
├── unit/           # 单元测试（Mock LLM / 无外部服务）
├── integration/    # 集成测试（torch、MCP、量化等）
├── e2e/            # 端到端（FastAPI TestClient、全链路）
├── fixtures/       # 共享 Mock / 工厂
└── conftest.py     # 全局 fixture + 自动 marker
```

## 覆盖范围

| 领域 | 主要测试文件 |
|------|-------------|
| Agent Runtime | `unit/test_agent.py`, `app/agents/tests/` |
| **Agent 自动化 (8.2)** | **`tests/agents/`** |
| Tool 系统 | `unit/test_tools.py` |
| Memory | `unit/test_enterprise_memory.py` |
| Workflow | `unit/test_workflow_engine.py`, `unit/test_workflow_human_approval.py` |
| RAG | `unit/test_rag_pipeline.py`, `unit/test_embedding.py`, `unit/test_vectorstore.py` |
| LLM Provider | `unit/test_llm_provider.py`, `app/llm/tests/` |

## 运行

```bash
cd backend

# 全量（含 integration）
pytest

# 默认 CI 同款：排除 integration
pytest -m "not integration"

# 仅单元
pytest ../tests/unit

# 仅 e2e
pytest ../tests/e2e

# Agent 自动化（Task 8.2）+ 报告
bash scripts/run_agent_tests.sh
# 报告: artifacts/agent_test_report.md

# 生成 JUnit 报告
bash scripts/run_tests.sh
# 或
pytest -m "not integration" --junitxml=artifacts/test-report.xml
```

## Markers

目录自动打标（见 `tests/conftest.py`）：

- `tests/unit/` → `@pytest.mark.unit`
- `tests/integration/` → `@pytest.mark.integration`
- `tests/e2e/` → `@pytest.mark.e2e`

## 共享 Fixtures

- `agent_config` — 轻量 AgentConfig
- `mock_llm` — `tests/fixtures/mock_llm.py`
