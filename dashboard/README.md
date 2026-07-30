# AI Infra Dashboard（Task 7.8）

本目录为 **Dashboard Demo 说明**；实现代码位于 `backend/app/dashboard/`。

## 访问方式

启动 API 服务后：

| 资源 | URL |
|------|-----|
| **Dashboard Demo（浏览器）** | [`/infra/dashboard/demo`](http://127.0.0.1:8000/infra/dashboard/demo) |
| **Overview JSON** | `GET /api/v1/infra/dashboard/overview` |

Demo 每 5 秒拉取一次 Overview，展示：

- 模型：运行状态、QPS、Latency、Token
- 全局：HTTP QPS、延迟、错误率、Gateway Token 累计
- GPU 利用率 / 显存 / 温度
- 缓存各层命中率
- Agent 调度器快照与服务发现摘要

## 本地快速体验

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

浏览器打开：`http://127.0.0.1:8000/infra/dashboard/demo`

产生指标示例：调用 Chat、Inference Gateway，或访问任意带 `InfraMetricsMiddleware` 的 API。

## 与 Software Team Dashboard 的区别

- 项目看板 API：`/api/v1/dashboard/*`（`app/api/dashboard/`）
- AI 基础设施看板：`/api/v1/infra/dashboard/*`（本 Task）
