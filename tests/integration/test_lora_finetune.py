"""LoRA / QLoRA 微调测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.finetune.lora.config import LoRAFinetuneConfig

DATA = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "finetune_demo"
    / "enterprise_sft.jsonl"
)

LORA_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "finetune_demo"
    / "lora_demo_config.json"
)


def test_lora_config_from_json() -> None:

    config = LoRAFinetuneConfig.from_json_file(
        LORA_CONFIG
    )

    assert config.lora_r == 4
    assert config.load_in_4bit is False
    assert "q_proj" in config.target_modules


def test_qwen_lora_config_template() -> None:

    path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "finetune_demo"
        / "lora_qwen_config.json"
    )

    config = LoRAFinetuneConfig.from_json_file(path)

    assert "Qwen" in config.model_path
    assert config.load_in_4bit is True
    assert config.lora_r == 8


@pytest.mark.integration
def test_lora_smoke_training(tmp_path: Path) -> None:

    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("datasets")
    pytest.importorskip("peft")

    from app.finetune.lora.trainer import run_lora_finetune

    config = LoRAFinetuneConfig(
        experiment_name="test_lora_smoke",
        training_data_path=str(DATA),
        model_path="sshleifer/tiny-gpt2",
        output_dir=str(tmp_path / "lora_out"),
        batch_size=1,
        learning_rate=5e-4,
        max_steps=3,
        max_seq_length=64,
        eval_ratio=0.2,
        lora_r=4,
        lora_alpha=8,
        load_in_4bit=False,
    )

    result = run_lora_finetune(config)

    assert result.adapter_dir.is_dir()
    assert result.report_json.is_file()
    assert result.report_markdown.is_file()
    assert result.training_time_seconds > 0

    report_text = result.report_markdown.read_text(
        encoding="utf-8"
    )

    assert "LoRA/QLoRA 实验报告" in report_text
    assert "训练耗时" in report_text
