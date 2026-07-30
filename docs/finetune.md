# 模型微调（Task 4.1）

企业领域适配训练流程，与 Agent Runtime **解耦**；产物通过 `model_path` / vLLM 配置接入推理。

## 训练流程

```text
JSONL 数据文件
    ↓
FinetuneDatasetBuilder（instruction / messages / text）
    ↓
HuggingFace Dataset（text 列）
    ↓
AutoTokenizer.from_pretrained(model_path)
    ↓
AutoModelForCausalLM.from_pretrained(model_path)
    ↓
transformers.Trainer（因果语言建模）
    ↓
Checkpoint（output_dir：权重 + tokenizer + finetune_config.json + eval_summary.json）
```

## 配置项

| 字段 | 说明 |
|------|------|
| `training_data_path` | JSONL 训练数据路径 |
| `model_path` | 基座模型（HF ID 或本地目录） |
| `output_dir` | Checkpoint 输出目录 |
| `batch_size` | `per_device_train_batch_size` |
| `learning_rate` | 学习率 |
| `num_train_epochs` / `max_steps` | 训练量 |
| `max_seq_length` | 截断长度 |
| `seed` | 随机种子（可复现） |

## 小规模 Demo

```powershell
cd backend
pip install -r requirements-llm.txt
pip install -r requirements-finetune.txt
python -m scripts.finetune_demo
```

默认配置：`data/finetune_demo/demo_config.json`（`sshleifer/tiny-gpt2`，`max_steps=8`）。

企业 Qwen 微调示例：将 `model_path` 改为 `Qwen/Qwen2.5-0.5B-Instruct`，增大 `max_steps`，并准备企业 JSONL。

## 模块路径

- `app/finetune/config.py` — `FinetuneConfig`
- `app/finetune/dataset.py` — 数据加载与格式化
- `app/finetune/trainer.py` — `FineTuneTrainer` / `run_finetune`
- `app/finetune/evaluator.py` — 指标汇总

## 测试

```powershell
python -m pytest tests/test_finetune.py -q -m "not integration"
# 已安装 torch/transformers 时：
python -m pytest tests/test_finetune.py::test_finetune_smoke -q
```
