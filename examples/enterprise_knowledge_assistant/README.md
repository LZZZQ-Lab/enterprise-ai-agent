# 企业知识助手 Demo

展示 **Enterprise LLM Application Platform** 的 RAG + Agent + FastAPI 能力：上传文档 → 自动建库 → 用户提问 → Agent 检索 → LLM 回答。

## 架构流程

```text
用户上传文档
    POST /api/v1/knowledge/documents
        → DocumentLoader → Splitter → Embedding → VectorStore

用户提问
    POST /api/v1/knowledge/ask
        → Retriever（引用来源）
        → ChatAgent + search_knowledge Tool
        → LLM（vLLM / OpenAI / local）
        → answer + sources
```

## 环境准备

在 `backend/.env` 中配置（vLLM 示例）：

```env
MODEL_PROVIDER=vllm
VLLM_ENDPOINT=http://127.0.0.1:8000/v1
MODEL_NAME=Qwen2.5
VLLM_MAX_TOKENS=256

EMBEDDING_PROVIDER=fake
VECTOR_STORE_PROVIDER=memory

ENABLE_KNOWLEDGE_TOOL=true
KNOWLEDGE_UPLOAD_DIR=./data/knowledge_uploads
```

本地无 GPU 时可先用 `EMBEDDING_PROVIDER=fake` + `VECTOR_STORE_PROVIDER=memory` 验证流程；生产请使用真实 Embedding 与 Chroma。

vLLM 启动见 [docs/vllm_deployment.md](../../docs/vllm_deployment.md)。

## 启动 API

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

打开 Swagger：http://localhost:8001/docs  

> **注意**：vLLM 默认占 **8000** 端口，Swagger 在 **8001**。若浏览器打开 `8000/docs` 会失败。请先访问 http://localhost:8001/health 确认返回 `{"status":"ok"}`。  
> 若 **health 正常但 /docs 白屏或一直转圈**，多为 CDN 加载失败：在 `backend/.env` 设置 `SWAGGER_UI_CDN=bootcdn` 并重启 API；或访问 http://localhost:8001/redoc 。

知识助手接口标签：**Knowledge Assistant**

## Demo 步骤

### 1. 上传企业文档

```powershell
curl -X POST "http://localhost:8001/api/v1/knowledge/documents" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@../examples/enterprise_knowledge_assistant/sample_docs/platform_intro.md"
```

期望：`success: true`，`chunks_ingested` ≥ 1。

### 2. 提问

```powershell
curl -X POST "http://localhost:8001/api/v1/knowledge/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"demo-1\",\"question\":\"平台支持哪些文档格式？\"}"
```

期望：`answer` 含 LLM 总结，`sources` 含检索片段与 `file_name`。

### 3. 使用 http 文件（可选）

见同目录 [demo.http](./demo.http)。

## 相关代码

| 模块 | 路径 |
|------|------|
| API | `backend/app/api/v1/knowledge.py` |
| 服务 | `backend/app/services/knowledge_assistant_service.py` |
| RAG | `backend/app/rag/pipeline.py` |
| Agent Tool | `backend/app/tools/knowledge_tool.py` |

## 测试

```powershell
cd backend
python -m pytest tests/test_knowledge_assistant_api.py -q
```
