# 模型量化性能报告（Task 4.3）

> 最新完整报告由 `python -m scripts.quantization_benchmark --copy-docs` 生成。以下为 **CPU Smoke**（`sshleifer/tiny-gpt2`）示例。

- **模型**: `sshleifer/tiny-gpt2`
- **环境**: Windows CPU（无 CUDA 时 FP16 以 FP32 权重加载，见 notes）

## 对比摘要

| 模式 | 模型大小(MiB) | 峰值显存(MiB) | 推理(ms) | tok/s | 加载(s) |
|------|---------------|---------------|----------|-------|---------|
| fp32 | 0.4 | N/A | 34.4 | 232.9 | ~35 |
| fp16 | 0.4 | N/A | 26.3 | 304.7 | ~10 |

## 相对 FP32 基线（示例）

- **fp16**: 权重大小约 100%（CPU 回退）；推理约 **1.31×** 加速（小模型 CPU 上主要为缓存效应，GPU 上 FP16 才显著降显存）

## GPU 全模式

在 WSL/CUDA 环境运行：

```bash
python -m scripts.quantization_benchmark \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --modes fp32,fp16,int8,int4 \
  --copy-docs
```

INT8/INT4 预期：权重大小与 **peak_allocated_mib** 明显低于 FP32，适合 4GB 显存卡。
