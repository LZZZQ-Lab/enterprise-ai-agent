# Task 2.6 性能基准

脚本位于 `backend/benchmark/`（在 `backend` 目录下运行）。

```bash
cd backend
IP=$(hostname -I | awk '{print $1}')

python -m benchmark.latency_test --backend vllm --base-url "http://${IP}:8000/v1"
python -m benchmark.throughput_test --backend vllm --base-url "http://${IP}:8000/v1"
python -m benchmark.latency_test --backend transformers
python -m benchmark.throughput_test --backend transformers

python -m benchmark.generate_report   # → docs/performance.md
```

结果 JSON：`backend/benchmark/results/`。
