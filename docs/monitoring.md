# AI Infra 监控（Task 4.5）

平台侧 **Prometheus 兼容** 指标，与 Agent Trace（`app/observability`）互补。

## 模块

| 文件 | 职责 |
|------|------|
| `app/monitoring/metrics.py` | Counter / Histogram / Gauge 注册与导出 |
| `app/monitoring/collector.py` | GPU 采集（nvidia-smi）+ 刮取前刷新 |
| `app/monitoring/middleware.py` | HTTP QPS / 延迟 |
| `app/monitoring/router.py` | `GET /metrics` |

## 指标

### GPU

| 指标 | 类型 | 说明 |
|------|------|------|
| `ai_infra_gpu_memory_used_mib` | gauge | 显存占用 |
| `ai_infra_gpu_memory_total_mib` | gauge | 显存总量 |
| `ai_infra_gpu_utilization_percent` | gauge | GPU 利用率 |

### 服务

| 指标 | 类型 | 说明 |
|------|------|------|
| `ai_infra_http_requests_total` | counter | 请求数（QPS 用 `rate()`） |
| `ai_infra_http_request_duration_seconds` | histogram | 端到端延迟 |
| `ai_infra_llm_requests_total` | counter | LLM 调用次数 |
| `ai_infra_llm_request_duration_seconds` | histogram | LLM 路径耗时 |
| `ai_infra_llm_tokens_total` | counter | Token（`type=prompt|completion`） |

Chat / 知识问答在 `ChatService`、`KnowledgeAssistantService` 中写入 LLM 指标；其余 API 由中间件统计 HTTP 指标。

## 使用

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001

curl http://127.0.0.1:8001/metrics
```

关闭中间件与路由挂载（仅保留代码）：`.env` 中 `ENABLE_INFRA_METRICS=false`。

## Prometheus 示例

```yaml
scrape_configs:
  - job_name: enterprise-ai-agent
    static_configs:
      - targets: ["host.docker.internal:8001"]
    metrics_path: /metrics
    scrape_interval: 15s
```

PromQL 示例：

- QPS：`sum(rate(ai_infra_http_requests_total[1m]))`
- P95 延迟：`histogram_quantile(0.95, sum(rate(ai_infra_http_request_duration_seconds_bucket[5m])) by (le, route))`
- Token 速率：`sum(rate(ai_infra_llm_tokens_total[1m])) by (type)`

## 测试

```bash
python -m pytest tests/test_monitoring.py -q
```

## 与 Phase 4 其他 Task

- **4.4** vLLM 压测：离线 benchmark JSON
- **4.5** 运行时 `/metrics`：生产可挂 Prometheus/Grafana
- **4.6** 结构化 Agent 链路日志，见 [structured_logging.md](./structured_logging.md)
