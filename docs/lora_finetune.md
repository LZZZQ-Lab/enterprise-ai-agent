# LoRA / QLoRA 微调（Task 4.2）

在 [finetune.md](./finetune.md) 全参微调基础上，通过 **PEFT LoRA** 与可选 **4bit QLoRA** 降低显存与训练成本，面向 **Qwen2.5** 等企业基座。

## 流程

```text
Base Model (如 Qwen/Qwen2.5-0.5B-Instruct)
    ↓
BitsAndBytes 4bit 量化（QLoRA，可选）
    ↓
prepare_model_for_kbit_training
    ↓
peft.LoraConfig + get_peft_model（注入 Adapter）
    ↓
transformers.Trainer 训练
    ↓
adapter/ 目录（仅 LoRA 权重）+ lora_experiment_report.md/json
```

## 配置

模块：`app/finetune/lora/config.py` → `LoRAFinetuneConfig`

| 字段 | 说明 |
|------|------|
| 继承 Task 4.1 | `training_data_path`, `model_path`, `batch_size`, `learning_rate` 等 |
| `lora.r` / `alpha` / `dropout` | LoRA 超参 |
| `lora.target_modules` | Qwen2.5 默认 attention + MLP 投影 |
| `lora.load_in_4bit` | QLoRA 开关 |
| `experiment_name` | 实验报告标题 |

示例：

- CPU/GPU smoke：`data/finetune_demo/lora_demo_config.json`（tiny-gpt2，无 4bit）
- Qwen2.5 QLoRA：`data/finetune_demo/lora_qwen_config.json`

## 运行 Demo

```powershell
cd backend
pip install -r requirements-llm.txt
pip install -r requirements-finetune.txt
python -m scripts.lora_finetune_demo
# Qwen QLoRA（需 GPU + bitsandbytes）：
python -m scripts.lora_finetune_demo --config data/finetune_demo/lora_qwen_config.json
```

## 实验报告

训练结束在 `output_dir` 生成：

- `lora_experiment_report.json`
- `lora_experiment_report.md`

记录项：

- **训练显存**：`peak_allocated_mib` / `nvidia-smi used`
- **训练时间**：秒
- **效果变化**：`eval_loss_before` → `eval_loss_after` 与 Δ

## 测试

```powershell
python -m pytest tests/test_lora_finetune.py -q -m "not integration"
python -m pytest tests/test_lora_finetune.py::test_lora_smoke_training -q
```

## 接入推理（后续 Task 4.3/4.4）

- Local：基座路径 + `PeftModel.from_pretrained(base, adapter_dir)`
- vLLM：合并 adapter 或使用 vLLM LoRA 加载（见后续文档）
