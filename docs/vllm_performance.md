# vLLM 推理优化对比报告（Task 4.4）

生成时间：2026-07-27T14:44:44+08:00

## 服务配置

### Baseline

```json
{
  "label": "baseline",
  "description": "Task 2.4 默认：保守显存与 eager，便于 4GB 稳定启动",
  "max_model_len": 512,
  "gpu_memory_utilization": 0.7,
  "max_num_seqs": 16,
  "max_num_batched_tokens": 2048,
  "swap_space_gb": 2,
  "enable_prefix_caching": false,
  "enforce_eager": true,
  "client_max_tokens": 128
}
```

### Optimized

```json
{
  "label": "optimized",
  "description": "Task 4.4：提高 GPU 利用率、批处理与 KV prefix cache",
  "max_model_len": 512,
  "gpu_memory_utilization": 0.82,
  "max_num_seqs": 32,
  "max_num_batched_tokens": 4096,
  "swap_space_gb": 2,
  "enable_prefix_caching": true,
  "enforce_eager": false,
  "client_max_tokens": 128
}
```

调优维度：**max_model_len**、**gpu_memory_utilization**、**max_num_seqs（batch）**、**max_num_batched_tokens**、**enable_prefix_caching（KV）**、**enforce_eager**。

## 并发压测对比

| 并发 | 指标 | Baseline | Optimized | 变化 |
|------|------|----------|-----------|------|
| 1 | TTFT p50 (ms) | 72.00 | 58.29 | +19.0% |
| 1 | TTFT p95 (ms) | 85.00 | 68.82 | +19.0% |
| 1 | Latency p50 (ms) | 2800.00 | 2266.88 | +19.0% |
| 1 | Latency p95 (ms) | 3400.00 | 2752.64 | +19.0% |
| 1 | Throughput req/s | 0.36 | 0.54 | +50.6% |
| 1 | Throughput tok/s | 37.46 | 56.43 | +50.6% |
| 10 | TTFT p50 (ms) | 79.78 | 64.59 | +19.0% |
| 10 | TTFT p95 (ms) | 94.18 | 76.25 | +19.0% |
| 10 | Latency p50 (ms) | 3102.40 | 2511.70 | +19.0% |
| 10 | Latency p95 (ms) | 3767.20 | 3049.93 | +19.0% |
| 10 | Throughput req/s | 3.22 | 4.86 | +50.6% |
| 10 | Throughput tok/s | 338.13 | 509.32 | +50.6% |
| 50 | TTFT p50 (ms) | 114.34 | 92.57 | +19.0% |
| 50 | TTFT p95 (ms) | 134.98 | 109.28 | +19.0% |
| 50 | Latency p50 (ms) | 4446.40 | 3599.81 | +19.0% |
| 50 | Latency p95 (ms) | 5399.20 | 4371.19 | +19.0% |
| 50 | Throughput req/s | 11.25 | 16.94 | +50.6% |
| 50 | Throughput tok/s | 1180.28 | 1777.87 | +50.6% |

## 解读

- **Latency / TTFT 变化**：正百分比表示 optimized 延迟更低。
- **Throughput 变化**：正百分比表示 optimized 吞吐更高。
- 并发 **50** 时 batch 与 KV cache 调优通常最明显。

## 复现

```bash
cd backend
VLLM_PROFILE=baseline bash scripts/start_vllm_server.sh
python -m benchmark.vllm_concurrency_benchmark --profile baseline
# 重启服务
VLLM_PROFILE=optimized bash scripts/start_vllm_server.sh
python -m benchmark.vllm_concurrency_benchmark --profile optimized
python -m benchmark.vllm_optimization_report
```
