# LLM Benchmark 性能对比报告（Task 8.3）

生成时间：2026-07-30T18:41:01+08:00

## 概述

对比 **Qwen (Transformers)**、**vLLM**、**OpenAI** 三类推理后端的延迟与吞吐表现。

| 指标 | 最优后端 |
| --- | --- |
| TTFT (p50) | OpenAI |
| Latency / Total (p50) | OpenAI |
| Token/s（单请求生成） | OpenAI |
| Throughput Token/s（多请求） | OpenAI |

## 单请求（Latency）

指标：TTFT、总延迟 (Latency)、生成 Token/s、Memory。

| Backend | Model | TTFT p50 (ms) | TTFT p95 (ms) | Latency p50 (ms) | Latency p95 (ms) | Token/s (p50) | Memory |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Qwen (Transformers) | Qwen/Qwen2.5-0.5B-Instruct | 2400.0 | 3200.0 | 9800.0 | 12000.0 | 12.00 | 3052 / 4096 MiB (GPU) |
| vLLM | Qwen/Qwen2.5-0.5B-Instruct | 820.0 | 1100.0 | 4100.0 | 5200.0 | 28.50 | 3055 / 4096 MiB (GPU) |
| OpenAI | gpt-4o-mini | 450.0 | 680.0 | 3200.0 | 4100.0 | 35.00 | 3055 / 4096 MiB (GPU) |

## 多请求（Throughput）

指标：并发请求数、Wall time、Requests/s、Token/s、Memory。

| Backend | Model | Requests | Concurrency | Wall (s) | Req/s | Token/s | Memory |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Qwen (Transformers) | Qwen/Qwen2.5-0.5B-Instruct | 8 | 2 | 96.00 | 0.083 | 4.25 | 3055 / 4096 MiB (GPU) |
| vLLM | Qwen/Qwen2.5-0.5B-Instruct | 8 | 2 | 48.00 | 0.167 | 8.50 | 3055 / 4096 MiB (GPU) |
| OpenAI | gpt-4o-mini | 8 | 2 | 38.00 | 0.211 | 10.74 | 3055 / 4096 MiB (GPU) |

## 运行方式

```bash
cd backend

# Mock（CI / 无 GPU / 无 API Key）
python -m benchmark.suite_runner --mock

# Live：vLLM 需先 start_vllm_server.sh；OpenAI 需 OPENAI_API_KEY
IP=$(hostname -I | awk '{print $1}')
python -m benchmark.suite_runner \
  --backends qwen vllm openai \
  --base-url "http://${IP}:8000/v1"
```

结果 JSON：`benchmark/results/` · 报告：`artifacts/benchmark_report.md`

> **Note:** 部分结果为 `--mock` 合成数据，仅供布局与 CI 验证。

