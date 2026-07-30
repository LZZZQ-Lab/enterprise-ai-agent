# vLLM 推理性能优化（Task 4.4）

在 Task 2.6 单并发基准之上，针对 **vLLM 服务参数** 做调优，并在并发 **1 / 10 / 50** 下对比 **TTFT、端到端 Latency、Throughput**。

## 优化项

| 维度 | Baseline | Optimized（默认） |
|------|----------|-------------------|
| GPU 利用率 | 0.70 | 0.82 |
| Batch（`max_num_seqs`） | 16 | 32 |
| Batched tokens | 2048 | 4096 |
| KV Cache | 关 | `--enable-prefix-caching` |
| CUDA Graph | `--enforce-eager` | 关闭 eager（更高吞吐） |
| max_model_len | 512 | 512（与 4GB 卡一致） |

配置定义：`backend/data/vllm_profiles.json`  
代码：`app/optimization/vllm_tuning.py`

## 启动服务

```bash
cd backend

# 优化前
VLLM_PROFILE=baseline bash scripts/start_vllm_server.sh

# 优化后（需重启进程）
VLLM_PROFILE=optimized bash scripts/start_vllm_server.sh
```

Windows 可通过 WSL：

```powershell
wsl bash -lc "cd /mnt/d/.../backend && VLLM_PROFILE=optimized bash scripts/start_vllm_server.sh"
```

WSL mirrored 网络时，压测 `--base-url` 使用网卡 IP 而非 `127.0.0.1`。

## Benchmark（`backend/benchmark/`）

```bash
cd backend

# 单次（当前服务应对应 --profile）
python -m benchmark.vllm_concurrency_benchmark --profile baseline
python -m benchmark.vllm_concurrency_benchmark --profile optimized

# 一键 mock（无 vLLM 也可生成对比报告）
python -m scripts.vllm_perf_benchmark --mock

# Live（先 baseline 服务 → 压测 → 换 optimized 重启 → 再压测）
python -m scripts.vllm_perf_benchmark --base-url "http://${IP}:8000/v1"
```

结果 JSON：

- `benchmark/results/vllm_concurrency_baseline.json`
- `benchmark/results/vllm_concurrency_optimized.json`

对比报告：

- `docs/vllm_performance.md`
- `artifacts/optimization/vllm/vllm_performance.md`

```bash
python -m benchmark.vllm_optimization_report
```

## 指标说明

- **TTFT**：首 token 时间（流式 SSE 首 chunk）
- **Latency**：单次请求总耗时（p50 / p95）
- **Throughput**：固定请求批次下的 req/s 与 tok/s

## 测试

```bash
python -m pytest tests/test_vllm_tuning.py -q
```

## 与 Task 2.6 / 4.3 关系

- **2.6**：vLLM vs Transformers 基础 latency/throughput
- **4.3**：Transformers 权重量化（显存）
- **4.4**：vLLM 服务侧 batch/KV/GPU 调优（吞吐与延迟）
