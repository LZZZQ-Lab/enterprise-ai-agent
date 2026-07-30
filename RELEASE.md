# Release 流程（Task 8.8）

Enterprise LLM Application Platform 采用 **语义化版本**（SemVer）与 [Keep a Changelog](https://keepachangelog.com/) 规范。

## 版本里程碑

| 版本 | 代号 | 说明 |
|------|------|------|
| **v0.1.0** | Platform Foundation | Phase 1–2：Agent 框架 · LLM Provider · Prompt · Docker 基线 |
| **v0.5.0** | Enterprise Platform | Phase 3–7：RAG/MCP · 软件团队 · Gateway · 生产化 |
| **v1.0.0** | Production Ready | Phase 8：测试 · Benchmark · 压测 · CI/CD · 安全 · 可观测性 · Release |

当前版本见根目录 [`VERSION`](VERSION)。

---

## 发布检查清单

### 1. 代码质量

```bash
cd backend
bash scripts/run_tests.sh
bash scripts/run_lint.sh
bash scripts/run_security_demo.sh --mock   # 可选
```

### 2. 版本与文档

- [ ] 更新 [`VERSION`](VERSION)（如 `1.0.0`）
- [ ] 更新 [`CHANGELOG.md`](CHANGELOG.md)（将 `[Unreleased]` 移至新版本节）
- [ ] 更新 [`README.md`](README.md) 版本徽章与版本说明
- [ ] 运行 OpenAPI 导出并校验版本一致：

```bash
cd backend
python scripts/export_openapi.py
python -c "
import json, pathlib
v = pathlib.Path('../VERSION').read_text().strip()
o = json.loads(pathlib.Path('../docs/openapi.json').read_text())['info']['version']
assert v == o, f'{v} != {o}'
print('VERSION OK:', v)
"
```

### 3. Docker（可选）

```bash
docker build -f docker/Dockerfile -t enterprise-ai-agent/api:release .
docker build -f deploy/Dockerfile -t enterprise-ai-agent/deploy:release .
```

### 4. Git Tag 与 GitHub Release

```bash
# 仓库根目录
git add VERSION CHANGELOG.md RELEASE.md README.md docs/openapi.json
git commit -m "release: v1.0.0 Production Ready (Phase 8)"
git tag -a v1.0.0 -m "v1.0.0 — Production Ready (Phase 8)"
git push origin main
git push origin v1.0.0
```

或使用发布脚本：

```bash
bash backend/scripts/release.sh 1.0.0
```

### 5. 创建 GitHub Release

```bash
gh release create v1.0.0 \
  --title "v1.0.0 — Production Ready" \
  --notes-file CHANGELOG.md
```

---

## CHANGELOG 分类说明

| 分类 | 用途 | 示例 |
|------|------|------|
| **Features** | 新功能、新模块 | Task 8.3 Benchmark 系统 |
| **Bug Fixes** | 缺陷修复 | Compose YAML 重复键 |
| **Breaking Changes** | 不兼容变更 | 启用 API Auth 后需 Token |

---

## 版本号规则

- **MAJOR**（1.x.x）：破坏性 API / 配置变更
- **MINOR**（x.1.x）：向后兼容的新功能
- **PATCH**（x.x.1）：向后兼容的问题修复

预发布标签（可选）：`v1.0.0-rc.1` · `v1.0.0-beta.1`

---

## 产物与报告（v1.0.0）

| 产物 | 路径 |
|------|------|
| 测试报告 | `backend/artifacts/test-report.xml` |
| Agent 测试报告 | `backend/artifacts/agent_test_report.md` |
| Benchmark 报告 | `backend/artifacts/benchmark_report.md` |
| 压测报告 | `backend/artifacts/stress_test_report.md` |
| 结构化日志 | `backend/artifacts/logs/structured.ndjson` |
| OpenAPI | `docs/openapi.json` |

---

## 首个 Release

**v1.0.0**（2026-07-30）为平台首个正式发布版本，涵盖 Phase 8 全部工程化能力。详见 [CHANGELOG.md](CHANGELOG.md) `[1.0.0]` 节。
