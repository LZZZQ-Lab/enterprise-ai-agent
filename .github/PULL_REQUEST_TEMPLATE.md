## 变更说明

<!-- 简要描述本 PR 的目的与实现方式（1–3 段） -->

## 变更类型

<!-- 勾选适用项 -->

- [ ] Bug 修复（非破坏性）
- [ ] 新功能（非破坏性）
- [ ] Breaking Change（破坏性变更，已在 CHANGELOG 说明）
- [ ] 文档 / Demo / 开源规范
- [ ] 重构 /  chore（无行为变化）
- [ ] CI / 构建

## 关联 Issue

<!-- 例如 Closes #123 / Fixes #456 -->

-

## 测试与验证

<!-- 说明如何验证；CI 未覆盖时请写手工步骤 -->

- [ ] `cd backend && bash scripts/run_tests.sh`（或 `pytest -m "not integration"`）
- [ ] `cd backend && bash scripts/run_lint.sh`
- [ ] Mock Demo（如适用）：`python examples/demo_XX_*.py` 或 `bash examples/run_all_demos.sh`
- [ ] OpenAPI / Compose 校验（如改动 API 或 Docker）

## 检查清单

- [ ] 已更新 [CHANGELOG.md](../CHANGELOG.md) 的 `[Unreleased]` 小节
- [ ] 未提交 `.env`、密钥、`project_runs/`、`.venv-*` 等敏感或本地产物
- [ ] 新增公开 API 已同步 `python backend/scripts/export_openapi.py`（如适用）
- [ ] 已阅读并遵循 [CONTRIBUTING.md](../CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)

## 截图 / 日志（可选）

<!-- Demo 输出、Swagger、Dashboard 等 -->
