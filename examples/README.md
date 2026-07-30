# Enterprise AI Platform — Demo 体系（Task 9.4）

6 个独立 Demo 脚本，覆盖平台核心能力。**默认 Mock 模式**：无需 GPU、API Key、Docker。

## 前置条件

```powershell
# 仅需 Python 3.11+ 与 backend 依赖
cd backend
pip install -r requirements.txt
cd ..
```

## Demo 一览

| 脚本 | 能力 | Mock 默认 | 说明 |
|------|------|-----------|------|
| [demo_01_chat.py](./demo_01_chat.py) | 基础 LLM 调用 | ✅ | `BaseLLM.chat()` · Message 组装 |
| [demo_02_rag.py](./demo_02_rag.py) | 知识库问答 | ✅ | FakeEmbedding · InMemory · 样例文档入库 |
| [demo_03_agent.py](./demo_03_agent.py) | Agent Tool Calling | ✅ | ChatAgent · `time` Tool · Agent Loop |
| [demo_04_workflow.py](./demo_04_workflow.py) | Workflow 执行 | ✅ | 线性 DAG · 人工审批暂停/恢复 |
| [demo_05_software_team.py](./demo_05_software_team.py) | AI 软件团队 | ✅ | PM→DevOps 全链路 · 产物落盘 |
| [demo_06_infra.py](./demo_06_infra.py) | 模型路由 / Gateway | ✅ | RouterEngine · InferenceGateway · Token 统计 |

## 快速运行

在 **仓库根目录** 执行：

```powershell
# 逐个运行
python examples/demo_01_chat.py
python examples/demo_02_rag.py
python examples/demo_03_agent.py
python examples/demo_04_workflow.py
python examples/demo_05_software_team.py
python examples/demo_06_infra.py

# 一键运行全部 Mock Demo
powershell -ExecutionPolicy Bypass -File examples/run_all_demos.ps1
# Linux / macOS / WSL
bash examples/run_all_demos.sh
```

## Mock 与 Live 模式

| 模式 | 标志 | 依赖 |
|------|------|------|
| **Mock**（默认） | 无额外参数 | 仅 `pip install -r backend/requirements.txt` |
| **Live** | `--live` | `backend/.env` 中配置 `API_KEY` · `MODEL_PROVIDER` 等 |

支持 Live 的 Demo：

```powershell
python examples/demo_01_chat.py --live
python examples/demo_02_rag.py --live      # 仅 LLM 走真实 Provider，Embedding 仍为 Fake
python examples/demo_03_agent.py --live
```

Demo 04 / 05 / 06 **仅 Mock**，已内置离线 Stub，不发起外部网络请求。

## 各 Demo 说明

### Demo 01 — 基础 LLM 调用

```powershell
python examples/demo_01_chat.py
```

输出 Mock LLM 对用户问题的回复，演示 `Message` 列表与 `ChatResult`。

### Demo 02 — 知识库问答（RAG）

```powershell
python examples/demo_02_rag.py
```

1. 导入 `examples/enterprise_knowledge_assistant/sample_docs/platform_intro.md`
2. Fake Embedding 写入内存向量库
3. 提问并返回答案 + 引用来源

### Demo 03 — Agent Tool Calling

```powershell
python examples/demo_03_agent.py
```

Mock LLM 第一轮返回 `time` Tool Call，AgentExecutor 执行 Tool 后第二轮生成最终答案。

### Demo 04 — Workflow 执行

```powershell
python examples/demo_04_workflow.py
```

- **Part A**：`product → architecture` 线性 DAG
- **Part B**：`Manager → Developer → Human Approval → Reviewer → Tester`，演示 `WAITING_APPROVAL` 与 `resume()`

### Demo 05 — AI 软件团队

```powershell
python examples/demo_05_software_team.py
python examples/demo_05_software_team.py --requirement "开发博客系统"
```

全链路 Mock：PM / Product / Architecture 使用 Demo LLM；Developer / Reviewer / Tester / DevOps 使用 Tool Bootstrap（无真实 LLM）。

产物目录：

```text
examples/_output/software_team/{run_id}/
  tasks.json
  reports/          PRD · Review · Test · Deployment 报告
  workspace/        生成的代码与文档
  logs/
```

### Demo 06 — 模型路由与 Gateway

```powershell
python examples/demo_06_infra.py
```

- **Model Router**：对话 / 代码 / 数学 / 长上下文 → 自动选择 Registry 模型
- **Inference Gateway**：Mock Backend 推理 + Token 统计

## 共享模块

| 文件 | 作用 |
|------|------|
| `_bootstrap.py` | 注入 `backend/` · 仓库根目录到 `sys.path` |
| `_mock.py` | 离线 LLM / Gateway Stub |
| `.gitignore` | 忽略 `_output/` 运行产物 |

## 与 REST API Demo 的关系

| 类型 | 路径 | 场景 |
|------|------|------|
| **脚本 Demo（本目录）** | `examples/demo_*.py` | 离线学习、CI、面试演示 |
| **API Demo** | [enterprise_knowledge_assistant/](./enterprise_knowledge_assistant/README.md) | Swagger · curl · 需启动 uvicorn |
| **应用层 Demo** | `backend/applications/*/run_*_demo.py` | 深度场景（MCP · Studio · Scheduler 等） |

## 故障排查

| 问题 | 处理 |
|------|------|
| `ModuleNotFoundError: app` | 在仓库根目录运行，或先 `cd backend && pip install -r requirements.txt` |
| Demo 05 较慢 | Developer/Tester 会执行本地 Tool；属正常，约 10–30 秒 |
| `--live` 报 API 错误 | 检查 `backend/.env` 中 `API_KEY` 与 `OPENAI_BASE_URL` |
| 想清空 Demo 05 产物 | 删除 `examples/_output/software_team/` |

## 相关文档

- [系统架构](../docs/architecture.md)
- [AI 软件团队](../docs/software_team.md)
- [目录结构](../docs/STRUCTURE.md)
