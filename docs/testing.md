# 测试指南（Task 8.1）

详见 [backend/tests/README.md](../backend/tests/README.md)。

## 快速开始

```bash
cd backend
bash scripts/run_tests.sh
```

## 分层

| 层 | 目录 | CI 默认 |
|----|------|---------|
| Unit | `tests/unit/` | ✅ 运行 |
| Integration | `tests/integration/` | ❌ 排除 |
| E2E | `tests/e2e/` | ✅ 运行 |

## 报告

- JUnit XML：`backend/artifacts/test-report.xml`
- Agent Test Report（Task 8.2）：`backend/artifacts/agent_test_report.md`

```bash
bash scripts/run_agent_tests.sh
```
