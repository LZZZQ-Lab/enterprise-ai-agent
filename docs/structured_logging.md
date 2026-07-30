# Agent 可观测性与结构化日志（Task 4.6）

定位 **Agent 执行问题**：通过 **Request ID** 关联 HTTP 请求与 **Trace**，输出完整 **LLM / Tool / 步骤 / Token** 链路。

## 模块 `app/logging/`

| 文件 | 职责 |
|------|------|
| `context.py` | `request_id` / `trace_id` / `session_id`（contextvars） |
| `structured.py` | 单行 **JSON structured logging** |
| `chain.py` | 从 Trace 构建 **完整 Agent 执行链路** |
| `trace_exporter.py` | `StructuredTraceExporter` → 日志 + JSON 文件 |
| `middleware.py` | `X-Request-ID` 注入 |

与 **`app/observability`** 分工：

- **observability**：Trace 事件模型、Collector、回放（Task 1.x）
- **logging**：生产可检索的结构化输出（Task 4.6）

## 记录内容

| 维度 | 来源 |
|------|------|
| Request ID | HTTP 中间件 / 响应头 `X-Request-ID` |
| Agent 步骤 | Planner / Workflow / Prompt 等 TraceEvent |
| Tool 调用 | `ToolEvent` |
| LLM 调用 | `LLMEvent`（含耗时） |
| Token 消耗 | Prompt 估算 + 每次 LLM `prompt_tokens` / `completion_tokens` |

## 启用

`.env`：

```env
ENABLE_STRUCTURED_LOGGING=true
ENABLE_AGENT_TRACE=true
TRACE_EXPORTER=structured
TRACE_EXPORT_DIR=./artifacts/agent_traces
```

- **`ENABLE_AGENT_TRACE`**：ChatAgent 开启 TraceCollector（默认 `false`，避免测试/开发噪音）
- **`TRACE_EXPORTER=structured`**：每次 Agent 执行结束写入 JSON + 结构化日志

其他导出器：`console` | `json` | `file`（见 `app/observability/exporter.py`）

## 输出示例

**stdout（JSON 行）**：

```json
{"timestamp":"...","event":"agent_chain_complete","request_id":"...","trace_id":"...","summary":{"llm_call_count":1,"tool_call_count":0,"total_tokens":128}}
```

**链路文件**：`artifacts/agent_traces/{trace_id}.json`

包含 `steps[]` 摘要 + 完整 `trace` 事件列表，便于 grep `request_id` 排查。

## 调试流程

1. 调用 API 时保存响应头 `X-Request-ID`
2. 在日志或 `artifacts/agent_traces/` 中搜索该 ID
3. 打开对应 JSON 查看 `steps` 与 `summary`
4. 或在代码中 `ChatAgent.replay_last_trace()`（需 `enable_trace`）

## 测试

```bash
cd backend
python -m pytest tests/test_structured_logging.py -q
```

## 与 Task 4.5

- **4.5 `/metrics`**：聚合 QPS、延迟、GPU（Prometheus）
- **4.6 结构化日志**：单次请求的 Agent 明细链路（排障）
