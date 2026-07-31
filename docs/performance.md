# Enterprise AI Platform — 项目性能报告

> **Task 9.7** · 汇总 LLM / RAG / Agent / vLLM / GPU 指标  
> 生成时间：2026-07-31  
> 原始数据：`backend/benchmark/results/` · `backend/artifacts/benchmark_report.md` · `backend/artifacts/stress_test_report.md`

---

## 1. 测试环境

| 项 | 配置 |
|----|------|
| **GPU** | NVIDIA GeForce RTX 2050 · **4 GB** VRAM |
| **CPU / OS** | x86_64 · Windows 11 + **WSL2** (Ubuntu) / CI: `ubuntu-latest` |
| **Python** | 3.11 |
| **模型（自托管）** | `Qwen/Qwen2.5-0.5B-Instruct` |
| **模型（云端基准）** | `gpt-4o-mini`（OpenAI 兼容 API） |
| **vLLM 版本** | `v0.10.2`（Docker 镜像 `vllm/vllm-openai:v0.10.2`） |
| **Platform 版本** | **1.0.0** |

### 部署方式

| 场景 | 部署形态 | 说明 |
|------|----------|------|
| **A. vLLM 实测** | WSL2 脚本 `start_vllm_server.sh` | Task 2.6 真机 GPU 延迟/吞吐 |
| **B. vLLM Docker** | `infra/docker/docker-compose.yml` | API + vLLM 两容器，GPU passthrough |
| **C. 生产栈** | `infra/deploy/docker-compose.yml` | Nginx + API + vLLM + Chroma + Redis |
| **D. 基准套件** | `benchmark.suite_runner --mock` | CI / 无 GPU，合成数据布局验证 |
| **E. 压测 Mock** | `loadtest.run_stress --mock` | Locust + 内置 Mock API |
| **F. 平台路径** | 本地 pytest / Demo | FakeEmbedding + InMemory · Mock LLM |

> **读表说明：** 标注 **Live** 为真实 GPU/API 或本机实测；**Mock** 为 CI 合成值，仅用于回归与报告结构，不可直接用于容量规划。

---

## 2. 性能总览

| 子系统 | 核心指标 | 最优参考值 | 数据来源 |
|--------|----------|------------|----------|
| **LLM Latency** | TTFT p50 | **69 ms** (vLLM Live) | Task 2.6 实测 |
| **LLM Throughput** | Token/s | **26.2** (vLLM Live, conc=2) | Task 2.6 实测 |
| **RAG Retrieval** | 检索 p50 | **0.16 ms** (InMemory, 6 chunks) | Task 9.7 本机实测 |
| **Agent Execution** | 端到端 p50 | **~50 ms** (Mock LLM + Tool) | Task 9.7 本机实测 |
| **vLLM QPS** | req/s @ conc=50 | **16.9** (Optimized, Mock suite) | Task 4.4 |
| **GPU Memory** | 占用 | **2855 / 4096 MiB** (vLLM 0.5B Live) | Task 2.6 nvidia-smi |

---

## 3. LLM — Latency（单请求）

### 3.1 vLLM 实测（Live · RTX 2050 · Task 2.6）

| 指标 | p50 | p95 | 备注 |
|------|-----|-----|------|
| **TTFT** | 69.4 ms | 78.3 ms | Time To First Token |
| **Total Latency** | 3012.8 ms | 3632.7 ms | 含生成 ~65 tokens |
| **Generation Token/s** | 23.14 | — | 单请求生成阶段 |
| **Avg Completion Tokens** | 65.0 | — | 5 runs |

### 3.2 多后端对比（Benchmark 套件 · Task 8.3）

| Backend | Model | TTFT p50 (ms) | TTFT p95 (ms) | Latency p50 (ms) | Latency p95 (ms) | Token/s (p50) | 数据 |
|---------|-------|--------------:|--------------:|-----------------:|-----------------:|--------------:|------|
| **vLLM** | Qwen2.5-0.5B | 820 | 1100 | 4100 | 5200 | 28.5 | Mock |
| **Qwen (Transformers)** | Qwen2.5-0.5B | 2400 | 3200 | 9800 | 12000 | 12.0 | Mock |
| **OpenAI** | gpt-4o-mini | 450 | 680 | 3200 | 4100 | 35.0 | Mock |
| **vLLM** | Qwen2.5-0.5B | **69.4** | **78.3** | **3012.8** | **3632.7** | **23.1** | **Live** |

---

## 4. LLM — Throughput（多请求）

### 4.1 vLLM 实测（Live · concurrency=2 · Task 2.6）

| 指标 | 值 |
|------|-----|
| Total Requests | 8 |
| Concurrency | 2 |
| Wall Time | 16.78 s |
| **Requests/s** | **0.477** |
| **Tokens/s** | **26.23** |
| Total Completion Tokens | 440 |

### 4.2 多后端对比（Benchmark 套件 · Task 8.3）

| Backend | Model | Requests | Concurrency | Wall (s) | **Req/s** | **Token/s** | 数据 |
|---------|-------|----------:|------------:|---------:|----------:|------------:|------|
| vLLM | Qwen2.5-0.5B | 8 | 2 | 48.0 | 0.167 | 8.50 | Mock |
| Qwen (Transformers) | Qwen2.5-0.5B | 8 | 2 | 96.0 | 0.083 | 4.25 | Mock |
| OpenAI | gpt-4o-mini | 8 | 2 | 38.0 | 0.211 | 10.74 | Mock |
| **vLLM** | Qwen2.5-0.5B | 8 | 2 | **16.78** | **0.477** | **26.23** | **Live** |

---

## 5. RAG — Retrieval Time

**配置：** `EMBEDDING_PROVIDER=fake` · `VECTOR_STORE_PROVIDER=memory` · 样例文档 6 chunks · Top-K=3

| 阶段 | p50 (ms) | p95 (ms) | 说明 |
|------|----------|----------|------|
| **向量检索** (`Retriever.retrieve`) | **0.16** | **0.18** | 本机实测，50 次采样 |
| 入库 (`ingest_file`, 6 chunks) | ~15–30 | — | 含 Fake Embedding，视 CPU 而定 |
| 完整 `ask()`（含 Mock LLM） | ~1–5 | — | LLM 占主导时为秒级 |

### RAG 生产环境参考（Chroma · 未在本报告实测）

| 规模 | 预期检索 | 建议 |
|------|----------|------|
| &lt; 10 万 chunk | 5–50 ms | Chroma + 本地 Embedding |
| &gt; 100 万 chunk | 50–200 ms+ | 分片 · HNSW 调参 · 缓存热查询 |

---

## 6. Agent — Execution Time

### 6.1 平台开销（Mock LLM · Tool Calling · 本机实测）

| 场景 | p50 (ms) | p95 (ms) | 说明 |
|------|----------|----------|------|
| **ChatAgent + time Tool**（2 轮 Loop） | **0.4** | **52.7** | Mock LLM，含 Prompt/Memory/Tool |
| Software Team 全链路 Mock | 10–30 s | — | 含 Developer Bootstrap / pytest Tool |

### 6.2 API 层（Locust 压测 · Mock API · Task 8.4）

| 端点 | 并发场景 | QPS | **平均延迟 (ms)** | 说明 |
|------|----------|-----|-------------------|------|
| `POST /api/v1/chat` | 10 users | 0.57 | **20.5** | Mock 后端，非真实 LLM |
| `POST /api/v1/chat` | 100 users | 1.88 | **18.4** | Mock 后端 |
| `GET /health` | 100 users | 4.35 | **2.4** | 纯 API 开销 |

### 6.3 Live Agent 估算（vLLM Live Latency 叠加）

| 路径 | 估算端到端 | 组成 |
|------|------------|------|
| 单轮对话（无 Tool） | **~3 s** | ≈ vLLM Total p50 |
| Tool Calling（2 轮 LLM） | **~6 s** | 2 × Latency p50 + Tool &lt;100 ms |
| RAG + Agent（1 检索 + 2 轮 LLM） | **~6 s** | 检索可忽略 + 2 × LLM |

---

## 7. vLLM — QPS（并发）

### 7.1 并发压测（Task 4.4 · Optimized Profile · Mock 套件）

| 并发 | TTFT p50 (ms) | Latency p50 (ms) | **QPS (req/s)** | **Token/s** | GPU Used (MiB) |
|------|--------------:|-----------------:|----------------:|------------:|-----------------:|
| 1 | 58.3 | 2266.9 | 0.54 | 56.4 | 2855 / 4096 |
| 10 | 64.6 | 2511.7 | **4.86** | 509.3 | 2855 / 4096 |
| 50 | 92.6 | 3599.8 | **16.94** | 1777.9 | 2855 / 4096 |

**Optimized 相对 Baseline（conc=50）：** QPS **+50.6%** · Token/s **+50.6%** · Latency p50 **−19%**

### 7.2 Baseline vs Optimized（conc=50）

| 指标 | Baseline | Optimized | 变化 |
|------|----------|-----------|------|
| **QPS** | 11.25 | **16.94** | +50.6% |
| **Token/s** | 1180.3 | **1777.9** | +50.6% |
| TTFT p50 (ms) | 114.3 | 92.6 | −19.0% |
| Latency p50 (ms) | 4446.4 | 3599.8 | −19.0% |

### 7.3 全栈 API 压测 QPS（Locust · Mock · Task 8.4）

| 场景 | 总请求 | **整体 QPS** | 平均延迟 (ms) | 错误率 |
|------|--------|-------------|---------------|--------|
| 10 并发用户 | 63 | **8.94** | 12.8 | 0% |
| 100 并发用户 | 93 | **13.48** | 12.1 | 0% |
| 1000 总请求 | 28 | **14.32** | 11.5 | 0% |

---

## 8. GPU — Memory

| 场景 | Backend / 组件 | Used (MiB) | Total (MiB) | 利用率 | 数据 |
|------|----------------|------------|-------------|--------|------|
| vLLM 推理（0.5B） | vLLM Live | **2855** | 4096 | **69.7%** | Task 2.6 实测 |
| vLLM 推理后 | vLLM Live | 2846 | 4096 | 69.5% | 推理完成 snapshot |
| Transformers 本地 | transformers Mock | 210 | 4096 | 5.1% | Mock 未加载权重 |
| Benchmark 套件 | vLLM / OpenAI Mock | 3055 | 4096 | 74.6% | Task 8.3 合成 |
| vLLM Docker 默认 | `--gpu-memory-utilization 0.65` | ~2650* | 4096 | ~65%* | 推荐 4GB 卡 |

\* 预估值，随 `VLLM_GPU_UTIL` / `max-model-len` 变化。

### vLLM 调优参数（4GB 显存）

| 参数 | Baseline | Optimized | 说明 |
|------|----------|-----------|------|
| `max-model-len` | 512 | 512 | 控制 KV Cache |
| `gpu-memory-utilization` | 0.70 | 0.82 | 显存占用上限 |
| `max-num-seqs` | 16 | 32 | 批并发 |
| `enable-prefix-caching` | false | true | 重复 Prompt 加速 |
| `enforce-eager` | true | false | 启动稳定 vs 吞吐 |

---

## 9. 指标对照图（Live vLLM vs Mock 套件）

```text
                    TTFT p50          Token/s (throughput)
vLLM Live (2.6)     69 ms             26.2
vLLM Mock (8.3)     820 ms            8.5
OpenAI Mock (8.3)   450 ms            10.7
Transformers Mock   2400 ms           4.3
```

Live 实测显著优于 Mock 合成值；**容量规划请以 Live 复现为准**。

---

## 10. 复现命令

### LLM Benchmark（Task 8.3）

```bash
cd backend

# Mock（CI 同款）
python -m benchmark.suite_runner --mock

# Live vLLM（需 GPU + start_vllm_server.sh）
IP=$(hostname -I | awk '{print $1}')
python -m benchmark.suite_runner --backends vllm qwen \
  --base-url "http://${IP}:8000/v1"
```

### vLLM 并发 QPS（Task 4.4）

```bash
VLLM_PROFILE=optimized bash scripts/start_vllm_server.sh
python -m benchmark.vllm_concurrency_benchmark --profile optimized
python -m benchmark.vllm_optimization_report
```

### 压测（Task 8.4）

```bash
pip install -r requirements-loadtest.txt
python -m loadtest.run_stress --mock --quick          # Mock
python -m loadtest.run_stress --host http://127.0.0.1:8001  # Live API
```

### RAG / Agent 路径（Task 9.7）

```bash
python examples/demo_02_rag.py    # RAG Mock 全链路
python examples/demo_03_agent.py    # Agent Tool Mock
```

---

## 11. 相关报告

| 报告 | 路径 |
|------|------|
| LLM Benchmark 明细 | [backend/artifacts/benchmark_report.md](../backend/artifacts/benchmark_report.md) |
| Locust 压测明细 | [backend/artifacts/stress_test_report.md](../backend/artifacts/stress_test_report.md) |
| vLLM 调优对比 | [backend/artifacts/optimization/vllm/vllm_performance.md](../backend/artifacts/optimization/vllm/vllm_performance.md) |
| 量化对比 | [docs/quantization.md](./quantization.md) |
| vLLM 部署 | [docs/vllm_deployment.md](./vllm_deployment.md) |

---

## 12. 总结

| 维度 | 结论 |
|------|------|
| **LLM** | 4GB 卡上 Qwen2.5-0.5B + vLLM Live TTFT **&lt;80 ms**，吞吐 **~26 token/s**（conc=2） |
| **RAG** | InMemory + Fake Embedding 检索 **&lt;1 ms**；生产 Chroma 需单独基准 |
| **Agent** | 平台 Mock 开销 **&lt;100 ms**；Live 端到端由 LLM 延迟主导（秒级） |
| **vLLM QPS** | Optimized @ conc=50 约 **17 req/s**（Mock 套件）；调优可提升 **~50%** |
| **GPU** | 0.5B 模型 vLLM 占用 **~2.8 GB / 4 GB**，仍有 API 共存空间 |

**建议：** 生产容量规划在目标 GPU 上运行 `benchmark.suite_runner`（无 `--mock`）与 `loadtest.run_stress`（Live）各一轮，将结果追加至本章表格。

---

<p align="center"><sub>Enterprise AI Platform Performance Report · Task 9.7 · v1.0.0</sub></p>
