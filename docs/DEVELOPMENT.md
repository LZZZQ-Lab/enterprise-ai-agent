# 开发指南（Task 4.8）

## 环境

Python 3.11+ · Docker 24+（Compose 校验）· 可选 GPU（vLLM）

## 本地 API

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt -r requirements-knowledge.txt
uvicorn app.main:app --reload --port 8001
```

## 测试（CI 同款）

```bash
cd backend
bash scripts/run_tests.sh
# 或: pytest -m "not integration"
```

集成：`python -m pytest tests -m integration -q`

## OpenAPI

```bash
cd backend
python scripts/export_openapi.py
```

## 规范

- 配置：`Settings` / `AgentConfig.from_env()`，禁止硬编码密钥
- Agent：经 `get_llm_client()`、Tool/RAG 抽象
- 模块：`observability`（Trace）· `monitoring`（Metrics）· `logging`（结构化）

## CI

`.github/workflows/test.yml` · `build.yml` — pytest、lint、Docker Build、OpenAPI artifact

## 发布

见 [RELEASE.md](../RELEASE.md)（Task 8.8）：

```bash
bash backend/scripts/release.sh 1.0.0
git tag -a v1.0.0 -m "v1.0.0"
gh release create v1.0.0 --title "v1.0.0" --notes-file CHANGELOG.md
```

见 [CONTRIBUTING.md](../CONTRIBUTING.md)、[API.md](./API.md)。
