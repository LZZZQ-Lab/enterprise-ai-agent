# 压力测试报告（Task 8.4 · Locust）

生成时间：2026-07-30T18:47:24+08:00
目标 Host：`http://127.0.0.1:18081`

## 测试范围

| 类别 | 端点 |
| --- | --- |
| API | `GET /health`, `POST /api/v1/chat` |
| Agent Workflow | `POST /api/v1/dashboard/projects`, `GET /api/v1/dashboard/workflow/{id}` |
| Inference Gateway | `POST /api/v1/inference/chat/completions`, `GET /api/v1/inference/stats` |

## 场景汇总

指标：**QPS**、**平均延迟 (ms)**、**错误率**

| 场景 | 总请求 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| 10 并发用户 (quick) | 63 | 8.94 | 12.8 | 0.00% |
| 100 并发用户 (quick) | 93 | 13.48 | 12.1 | 0.00% |
| 1000 总请求 (quick) | 28 | 14.32 | 11.5 | 0.00% |

### 10 并发用户 (quick)

#### 按类别

| 类别 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API | 20 | 2.84 | 6.4 | 0.00% |
| Agent Workflow | 15 | 2.13 | 19.4 | 0.00% |
| Inference Gateway | 28 | 3.97 | 13.8 | 0.00% |

#### 端点明细

| 端点 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API GET /health | 16 | 2.27 | 2.9 | 0.00% |
| API POST /api/v1/chat | 4 | 0.57 | 20.5 | 0.00% |
| Gateway GET /api/v1/inference/stats | 8 | 1.14 | 2.1 | 0.00% |
| Gateway POST /api/v1/inference/chat/completions | 20 | 2.84 | 18.5 | 0.00% |
| Workflow GET /api/v1/dashboard/workflow/{id} | 6 | 0.85 | 17.9 | 0.00% |
| Workflow POST /api/v1/dashboard/projects | 9 | 1.28 | 20.4 | 0.00% |

### 100 并发用户 (quick)

#### 按类别

| 类别 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API | 43 | 6.23 | 7.2 | 0.00% |
| Agent Workflow | 27 | 3.91 | 18.8 | 0.00% |
| Inference Gateway | 23 | 3.33 | 13.4 | 0.00% |

#### 端点明细

| 端点 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API GET /health | 30 | 4.35 | 2.4 | 0.00% |
| API POST /api/v1/chat | 13 | 1.88 | 18.4 | 0.00% |
| Gateway GET /api/v1/inference/stats | 7 | 1.01 | 2.6 | 0.00% |
| Gateway POST /api/v1/inference/chat/completions | 16 | 2.32 | 18.1 | 0.00% |
| Workflow GET /api/v1/dashboard/workflow/{id} | 14 | 2.03 | 18.2 | 0.00% |
| Workflow POST /api/v1/dashboard/projects | 13 | 1.88 | 19.5 | 0.00% |

### 1000 总请求 (quick)

#### 按类别

| 类别 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API | 13 | 6.65 | 5.4 | 0.00% |
| Agent Workflow | 8 | 4.09 | 21.3 | 0.00% |
| Inference Gateway | 7 | 3.58 | 11.6 | 0.00% |

#### 端点明细

| 端点 | 请求数 | QPS | 平均延迟 (ms) | 错误率 |
| --- | ---: | ---: | ---: | ---: |
| API GET /health | 11 | 5.63 | 3.1 | 0.00% |
| API POST /api/v1/chat | 2 | 1.02 | 17.9 | 0.00% |
| Gateway GET /api/v1/inference/stats | 3 | 1.53 | 2.2 | 0.00% |
| Gateway POST /api/v1/inference/chat/completions | 4 | 2.05 | 18.7 | 0.00% |
| Workflow GET /api/v1/dashboard/workflow/{id} | 5 | 2.56 | 21.8 | 0.00% |
| Workflow POST /api/v1/dashboard/projects | 3 | 1.53 | 20.3 | 0.00% |

## 运行方式

```bash
cd backend
pip install -r requirements-loadtest.txt

# Mock（内置轻量 API，无需 LLM）
python -m loadtest.run_stress --mock --quick

# Live（需 API 运行于 8001）
python -m loadtest.run_stress --host http://127.0.0.1:8001
```

原始 CSV：`loadtest/results/` · 报告：`artifacts/stress_test_report.md`

> **Note:** 本次使用 Mock API，延迟为合成值，仅供 CI / 布局验证。

