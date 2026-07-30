# 贡献指南

感谢你对 **Enterprise AI Platform**（企业级大模型应用平台）的关注与贡献。本文说明如何参与开发、提交 PR 及通过 CI 检查。

## 行为准则

参与本项目即表示你同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 我能贡献什么？

| 类型 | 说明 |
|------|------|
| Bug 修复 | 使用 [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.yml) |
| 功能建议 | 使用 [功能建议模板](.github/ISSUE_TEMPLATE/feature_request.yml) |
| 文档 / 博客 | `docs/` · `examples/` · `docs/blog/` |
| Demo | `examples/demo_*.py`（需支持 Mock 模式） |
| 测试 | `tests/` · `backend/app/**/tests/` |

提交 PR 前请先搜索 [已有 Issues](https://github.com/LZZZQ-Lab/enterprise-ai-agent/issues)，避免重复劳动。

## 开发环境

**要求：** Python 3.11+ · Git · （可选）Docker 24+

```powershell
git clone https://github.com/LZZZQ-Lab/enterprise-ai-agent.git
cd enterprise-ai-agent/backend
copy .env.example .env
pip install -r requirements.txt -r requirements-knowledge.txt
pip install -r requirements-dev.txt
```

启动 API：

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

详细说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 分支与提交

1. Fork 仓库并从 `main` 创建分支：`feature/xxx` · `fix/xxx` · `docs/xxx`
2. 保持提交原子、信息明确（英文或中文均可）
3. 不要提交：`.env`、API Key、`project_runs/`、`.venv-*`、`examples/_output/`

## 代码规范

- **配置**：使用 `app/config/settings.py` 与 `.env`，禁止硬编码密钥
- **LLM**：业务代码经 `get_llm_client()` / `BaseLLM`，不直连 HTTP
- **Agent**：System Prompt 放在 `app/prompts/templates/`，不在 Agent 内硬编码长文本
- **导入**：新代码优先 `core/` · `llm/` · `knowledge/` · `apps/`（见 [docs/STRUCTURE.md](docs/STRUCTURE.md)）
- **Lint**：`cd backend && bash scripts/run_lint.sh`（ruff E9/F821）

## 测试

CI 默认与本地推荐命令一致：

```powershell
cd backend
bash scripts/run_tests.sh
# 等价于: pytest -m "not integration"
```

其他：

```powershell
pytest ../tests/unit -q
bash examples/run_all_demos.sh    # Mock Demo 全量
python scripts/export_openapi.py  # 改动 API 时
```

集成测试（需额外依赖）：`pytest -m integration`

## Pull Request 流程

1. 更新 [CHANGELOG.md](CHANGELOG.md) 的 **`[Unreleased]`** 小节
2. 填写 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)
3. 确保 CI 通过：
   - **Test** — lint · pytest · OpenAPI · Compose 校验
   - **Mock Demos** — `examples/run_all_demos.sh`
   - **Build** — Docker 镜像构建（merge 前由 Test 工作流触发）
4. 等待 Maintainer Review；必要时 rebase `main`

## 版本发布（Maintainers）

见 [RELEASE.md](RELEASE.md)：

```bash
bash backend/scripts/release.sh X.Y.Z
git tag -a vX.Y.Z -m "vX.Y.Z"
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file CHANGELOG.md
```

## 目录速查

| 路径 | 说明 |
|------|------|
| `backend/app/` | 平台实现（Legacy `app.*`） |
| `core/` · `llm/` · `knowledge/` | Canonical 模块 facade |
| `tests/` | pytest 主目录 |
| `examples/` | Mock Demo 体系 |
| `docs/` | 架构 · API · 博客 |
| `.github/workflows/` | CI/CD |

## 获取帮助

- [README.md](README.md) · [docs/architecture.md](docs/architecture.md)
- [examples/README.md](examples/README.md)
- [Issues](https://github.com/LZZZQ-Lab/enterprise-ai-agent/issues)

再次感谢你的贡献。
