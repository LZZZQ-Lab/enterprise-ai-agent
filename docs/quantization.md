# 模型量化优化（Task 4.3）

降低 GPU 显存占用，对比 **原模型（FP32）** 与 **FP16 / INT8 / INT4** 的模型大小、显存与推理速度。

## 模块

| 文件 | 职责 |
|------|------|
| `app/optimization/quantization.py` | 加载策略、`QuantizationMode`、`profile_mode` |
| `app/optimization/benchmark.py` | 多模式对比、`quantization_report.md/json` |

## 量化方式

| 模式 | 说明 | 依赖 |
|------|------|------|
| **FP32** | 原精度基线 | transformers |
| **FP16** | 半精度权重 | CUDA 推荐 |
| **INT8** | 8bit 权重量化 | CUDA + bitsandbytes |
| **INT4** | NF4 4bit 量化 | CUDA + bitsandbytes |

与 Task 4.2 QLoRA 的 4bit 加载方式一致，便于统一运维认知。

## 运行 Benchmark

```powershell
cd backend
pip install -r requirements-llm.txt
pip install -r requirements-finetune.txt

# Smoke（tiny 模型，CPU 可跑 FP32/FP16）
python -m scripts.quantization_benchmark

# Qwen2.5 全模式（需 GPU）
python -m scripts.quantization_benchmark --model Qwen/Qwen2.5-0.5B-Instruct --copy-docs
```

输出目录默认：`artifacts/optimization/quantization/`

- `quantization_report.json`
- `quantization_report.md`

加 `--copy-docs` 会同步写入 `docs/quantization_report.md`。

## 报告指标

- **模型大小 (MiB)**：加载后参数 tensor 估算
- **显存占用**：`peak_allocated_mib` / nvidia-smi
- **推理速度**：固定 prompt 下 `generate` 平均耗时与 tok/s
- **对比 FP32**：体积降幅、推理加速比

## 测试

```powershell
python -m pytest tests/test_quantization.py -q -m "not integration"
python -m pytest tests/test_quantization.py::test_benchmark_fp32_fp16_smoke -q
```

## 与平台关系

- **不修改** Agent / vLLM Provider；本地 `LocalLLMProvider` 已支持 `LOCAL_MODEL_4BIT`（4.1 前已有）。
- vLLM 侧 AWQ/GPTQ 部署在 Task 4.7 文档化；本模块聚焦 **Transformers 加载路径** 的可复现实验。
