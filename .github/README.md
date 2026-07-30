# GitHub 工程规范（Task 9.6）

本目录包含 Enterprise AI Platform 的 CI/CD 与社区模板。

## Workflows

| 文件 | 触发 | 说明 |
|------|------|------|
| [workflows/test.yml](workflows/test.yml) | push / PR → main, master, develop | ruff · pytest · OpenAPI · Compose 校验 |
| [workflows/build.yml](workflows/build.yml) | Test 成功后 | Docker 镜像构建与健康检查 |
| [workflows/demos.yml](workflows/demos.yml) | push / PR | 运行 `examples/run_all_demos.sh`（Mock） |

## Issue 模板

- [bug_report.yml](ISSUE_TEMPLATE/bug_report.yml) — Bug 报告
- [feature_request.yml](ISSUE_TEMPLATE/feature_request.yml) — 功能建议
- [config.yml](ISSUE_TEMPLATE/config.yml) — 禁用空白 Issue · 文档链接

## Pull Request

- [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md)

## 依赖更新

- [dependabot.yml](dependabot.yml) — 每周扫描 pip（backend）与 GitHub Actions

## 仓库根目录配套文件

| 文件 | 说明 |
|------|------|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献流程 |
| [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Contributor Covenant 2.1 |
| [../SECURITY.md](../SECURITY.md) | 漏洞报告 |
| [../LICENSE](../LICENSE) | MIT |
| [../CHANGELOG.md](../CHANGELOG.md) | Keep a Changelog |
