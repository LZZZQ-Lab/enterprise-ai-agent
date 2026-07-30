# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

变更类型：**Features** · **Bug Fixes** · **Breaking Changes**

---

## [Unreleased]

### Features

- **Phase 9 开源就绪（Task 9.1–9.6）**
  - 模块化目录：`apps/` · `core/` · `llm/` · `knowledge/` · `infra/` · [docs/STRUCTURE.md](docs/STRUCTURE.md)
  - 重写 [README.md](README.md) · 系统架构 [docs/architecture.md](docs/architecture.md)
  - Demo 体系：`examples/demo_01`–`demo_06`（Mock 离线）· [examples/README.md](examples/README.md)
  - 技术博客：[docs/blog/](docs/blog/)（6 篇）
  - GitHub 规范：Issue/PR 模板 · Dependabot · Mock Demos CI · CONTRIBUTING · CoC · SECURITY
- **性能报告汇总（Task 9.7）**：重写 [docs/performance.md](docs/performance.md)（LLM / RAG / Agent / vLLM QPS / GPU）
- **面试材料（Task 9.8）**：[docs/interview/](docs/interview/)（项目介绍 · 架构问答 · 技术深度）
- `infra/docker/` · `infra/k8s/` 迁移；`docker/` 兼容入口保留
- `tests/` 移至仓库根目录；`app/tools` 循环导入修复（lazy export）

### Bug Fixes

- 修复 `app/tools/__init__.py` 与 RAG 导入链导致的循环依赖

---

## [1.0.0] - 2026-07-30

**Production Ready（Phase 8）** — 首个正式发布版本。

### Features

- **测试体系（Task 8.1）**：`tests/{unit,integration,e2e}` 分层 · pytest 报告 · `scripts/run_tests.sh`
- **Agent 自动化测试（Task 8.2）**：Mock LLM · `tests/agents/` · `agent_test_report.md`
- **LLM Benchmark（Task 8.3）**：Qwen / vLLM / OpenAI 对比 · `benchmark/` · `benchmark_report.md`
- **压力测试（Task 8.4）**：Locust · API / Workflow / Gateway · `loadtest/` · `stress_test_report.md`
- **CI/CD（Task 8.5）**：`.github/workflows/test.yml` · `build.yml`（pytest · lint · Docker Build）
- **安全能力（Task 8.6）**：API 认证 · Secret 管理 · 输入过滤 · Prompt Injection 防护 · 危险操作审批 · `security/`
- **结构化日志升级（Task 8.7）**：`observability/logging/` · Request/User/Project/Agent/Workflow ID · Token · Latency · ELK/Loki JSON
- **Release 流程（Task 8.8）**：`VERSION` · `CHANGELOG.md` · `RELEASE.md` · 发布脚本

### Bug Fixes

- 修复 `docker/docker-compose.yml` 重复 `args` 导致 Compose 校验失败
- 修复 `ModelInfo` / `ScenarioSummary` 等 lint 门禁问题
- 修复 WSL vLLM 联调 `tool_choice` / `max_tokens` / 网络可达性相关配置说明

### Breaking Changes

- 默认仍兼容 Phase 7 配置；**启用 `ENABLE_API_AUTH=true` 时**所有受保护 API 需 Bearer / `X-API-Key`
- 危险 Tool（`terminal` / `code` 等）在 `ENABLE_DANGEROUS_TOOL_APPROVAL=true` 时需 Admin 审批后执行

---

## [0.5.0] - 2026-07-27

**Enterprise Platform（Phase 3–7）** — 企业能力与生产化中间里程碑。

### Features

- **Phase 3**：RAG / MCP / Multi-Agent · 企业知识助手 API · `examples/enterprise_knowledge_assistant/`
- **Phase 4**：量化 benchmark · vLLM 调优 · Prometheus `/metrics` · 结构化 Agent 链路日志 · `deploy/` 生产栈
- **Phase 5**：AI 软件团队 Agent（PM → DevOps）· 全链路 Demo · `docs/software_team.md`
- **Phase 6–7**：Inference Gateway · Service Discovery · Model Registry · Infra Dashboard
- **CI 初版**：GitHub Actions pytest · Compose 校验 · OpenAPI 导出
- **工程文档**：`docs/DEVELOPMENT.md` · `docs/API.md` · `CONTRIBUTING.md`

### Bug Fixes

- FastAPI OpenAPI 元数据与 Swagger CDN 国内镜像配置
- Agent 测试收集路径与 import 错误修复

### Breaking Changes

- 配置统一迁移至 `app/config/settings.py`；旧 `app/core/config` 仅为兼容转发
- `MODEL_PROVIDER` 扩展为 `openai | local | vllm | gateway`，需按 Provider 配置对应环境变量

---

## [0.1.0] - 2026-07

**Platform Foundation（Phase 1–2）** — 首个可运行平台基线。

### Features

- Agent Runtime · Registry · Factory · ChatAgent · AgentExecutor（Agent Loop）
- LLM Provider：OpenAI · Local（Qwen）· vLLM
- Prompt 系统：`PromptBuilder` · `templates/`
- 统一 Settings · `.env` 驱动 · 基础 pytest
- Docker 轻量栈（API + vLLM）· `benchmark/` 性能基准（Task 2.6）
- vLLM 部署脚本与 `docs/vllm_deployment.md`

### Bug Fixes

- （初始基线版本）

### Breaking Changes

- （初始基线版本，无破坏性变更）

---

[Unreleased]: https://github.com/LZZZQ-Lab/enterprise-ai-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/LZZZQ-Lab/enterprise-ai-agent/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/LZZZQ-Lab/enterprise-ai-agent/compare/v0.1.0...v0.5.0
[0.1.0]: https://github.com/LZZZQ-Lab/enterprise-ai-agent/releases/tag/v0.1.0
