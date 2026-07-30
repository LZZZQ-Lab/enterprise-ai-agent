from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logger import logger
from app.finetune.config import FinetuneConfig
from app.finetune.dataset import FinetuneDatasetBuilder
from app.finetune.evaluator import FinetuneEvaluator


@dataclass
class FinetuneResult:
    """
    训练运行结果摘要。
    """

    output_dir: Path

    train_loss: float | None

    eval_loss: float | None

    global_step: int

    metrics: dict[str, Any]


class FineTuneTrainer:
    """
    Transformers Trainer 微调流程封装。

    数据 → Dataset → Tokenizer → Model → Trainer → Checkpoint
    """

    def __init__(
        self,
        config: FinetuneConfig,
    ) -> None:

        self._config = config

    def run(self) -> FinetuneResult:

        self._set_seed()

        output_dir = self._config.resolve_output_dir()

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._config.save_json()

        builder = FinetuneDatasetBuilder(
            self._config
        )

        train_dataset, eval_dataset = (
            builder.build_hf_dataset()
        )

        tokenizer = self._load_tokenizer()

        model = self._load_model()

        tokenized_train = train_dataset.map(
            lambda batch: self._tokenize_batch(
                batch,
                tokenizer,
            ),
            batched=True,
            remove_columns=train_dataset.column_names,
        )

        tokenized_eval = None

        if eval_dataset is not None:

            tokenized_eval = eval_dataset.map(
                lambda batch: self._tokenize_batch(
                    batch,
                    tokenizer,
                ),
                batched=True,
                remove_columns=eval_dataset.column_names,
            )

        training_args = self._build_training_arguments(
            output_dir,
        )

        from transformers import DataCollatorForLanguageModeling
        from transformers import Trainer

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_train,
            eval_dataset=tokenized_eval,
            tokenizer=tokenizer,
            data_collator=data_collator,
        )

        train_result = trainer.train()

        trainer.save_model(str(output_dir))

        tokenizer.save_pretrained(str(output_dir))

        eval_metrics: dict[str, Any] = {}

        if tokenized_eval is not None:

            eval_metrics = trainer.evaluate()

        evaluator = FinetuneEvaluator(
            self._config
        )

        summary = evaluator.build_summary(
            train_result.metrics,
            eval_metrics,
        )

        evaluator.save_summary(
            output_dir,
            summary,
        )

        logger.info(
            "Finetune completed: output=%s step=%s",
            output_dir,
            train_result.global_step,
        )

        return FinetuneResult(
            output_dir=output_dir,
            train_loss=train_result.metrics.get(
                "train_loss"
            ),
            eval_loss=eval_metrics.get("eval_loss"),
            global_step=int(
                train_result.global_step
            ),
            metrics=summary,
        )

    def _set_seed(self) -> None:

        import random

        import numpy as np
        import torch

        seed = self._config.seed

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        if torch.cuda.is_available():

            torch.cuda.manual_seed_all(seed)

    def _load_tokenizer(self):

        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            self._config.model_path,
            trust_remote_code=True,
        )

        if tokenizer.pad_token is None:

            tokenizer.pad_token = tokenizer.eos_token

        return tokenizer

    def _load_model(self):

        from transformers import AutoModelForCausalLM

        return AutoModelForCausalLM.from_pretrained(
            self._config.model_path,
            trust_remote_code=True,
        )

    def _tokenize_batch(
        self,
        batch: dict[str, list[str]],
        tokenizer,
    ) -> dict[str, Any]:

        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=self._config.max_seq_length,
            padding=False,
        )

    def _build_training_arguments(
        self,
        output_dir: Path,
    ):
        from transformers import TrainingArguments

        kwargs: dict[str, Any] = {
            "output_dir": str(output_dir),
            "per_device_train_batch_size": (
                self._config.batch_size
            ),
            "learning_rate": self._config.learning_rate,
            "num_train_epochs": self._config.num_train_epochs,
            "logging_steps": self._config.logging_steps,
            "save_steps": self._config.save_steps,
            "save_total_limit": 2,
            "report_to": [],
            "seed": self._config.seed,
            "warmup_ratio": self._config.warmup_ratio,
            "weight_decay": self._config.weight_decay,
            "gradient_accumulation_steps": (
                self._config.gradient_accumulation_steps
            ),
            "bf16": self._config.bf16,
            "fp16": self._config.fp16,
        }

        if self._config.max_steps > 0:

            kwargs["max_steps"] = self._config.max_steps

        return TrainingArguments(**kwargs)


def run_finetune(
    config: FinetuneConfig,
) -> FinetuneResult:

    return FineTuneTrainer(config).run()
