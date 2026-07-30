"""Finetune 模块单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.finetune.config import FinetuneConfig
from app.finetune.dataset import FinetuneDatasetBuilder
from app.finetune.evaluator import FinetuneEvaluator

DATA = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "finetune_demo"
    / "enterprise_sft.jsonl"
)


def test_dataset_format_and_split() -> None:

    config = FinetuneConfig(
        training_data_path=str(DATA),
        model_path="sshleifer/tiny-gpt2",
        eval_ratio=0.2,
        seed=42,
    )

    builder = FinetuneDatasetBuilder(config)

    train_ds, eval_ds = builder.build_hf_dataset()

    assert len(train_ds) >= 1
    assert eval_ds is not None
    assert len(eval_ds) >= 1

    sample = train_ds[0]["text"]

    assert "### User:" in sample
    assert "### Assistant:" in sample


def test_config_roundtrip(tmp_path: Path) -> None:

    config = FinetuneConfig(
        training_data_path=str(DATA),
        model_path="sshleifer/tiny-gpt2",
        output_dir=str(tmp_path / "out"),
        batch_size=4,
        learning_rate=1e-4,
    )

    saved = config.save_json()

    loaded = FinetuneConfig.from_json_file(saved)

    assert loaded.batch_size == 4
    assert loaded.learning_rate == 1e-4


def test_evaluator_summary() -> None:

    config = FinetuneConfig(
        training_data_path=str(DATA),
        model_path="tiny",
    )

    evaluator = FinetuneEvaluator(config)

    summary = evaluator.build_summary(
        {"train_loss": 1.23, "epoch": 1.0},
        {"eval_loss": 1.11},
    )

    assert summary["train_loss"] == 1.23
    assert summary["eval_loss"] == 1.11


@pytest.mark.integration
def test_finetune_smoke(tmp_path: Path) -> None:

    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    pytest.importorskip("datasets")

    from app.finetune.trainer import run_finetune

    config = FinetuneConfig(
        training_data_path=str(DATA),
        model_path="sshleifer/tiny-gpt2",
        output_dir=str(tmp_path / "checkpoint"),
        batch_size=1,
        learning_rate=5e-5,
        max_steps=2,
        max_seq_length=64,
        eval_ratio=0.0,
        logging_steps=1,
        save_steps=100,
    )

    result = run_finetune(config)

    assert result.global_step >= 2
    assert (result.output_dir / "config.json").exists()
    assert (result.output_dir / "eval_summary.json").exists()
