from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logger import logger
from app.finetune.dataset import FinetuneDatasetBuilder
from app.finetune.evaluator import FinetuneEvaluator
from app.finetune.lora.config import LoRAFinetuneConfig
from app.finetune.lora.report import LoRAExperimentReport
from app.finetune.trainer import FinetuneResult
from app.finetune.trainer import FineTuneTrainer


@dataclass
class LoRAFinetuneResult(FinetuneResult):
    """
    LoRA 训练结果 + 实验报告路径。
    """

    adapter_dir: Path

    report_json: Path

    report_markdown: Path

    training_time_seconds: float

    gpu_memory: dict[str, Any]


class LoRAFineTuneTrainer(FineTuneTrainer):
    """
    Base Model → (4bit) → LoRA Adapter → Trainer → Save Adapter
    """

    def __init__(
        self,
        config: LoRAFinetuneConfig,
    ) -> None:

        super().__init__(config)

        self._lora_config = config

    def run(self) -> LoRAFinetuneResult:

        import torch

        self._set_seed()

        output_dir = self._config.resolve_output_dir()

        adapter_dir = Path(
            self._lora_config.resolve_lora_output_dir()
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        adapter_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._config.save_json()

        if torch.cuda.is_available():

            torch.cuda.reset_peak_memory_stats()

        memory_before = self._snapshot_memory()

        builder = FinetuneDatasetBuilder(
            self._config
        )

        train_dataset, eval_dataset = (
            builder.build_hf_dataset()
        )

        tokenizer = self._load_tokenizer()

        model = self._load_model_with_lora()

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

        eval_before: dict[str, Any] = {}

        if tokenized_eval is not None:

            eval_before = trainer.evaluate()

        start = time.perf_counter()

        train_result = trainer.train()

        elapsed = time.perf_counter() - start

        memory_after = self._snapshot_memory()

        model.save_pretrained(str(adapter_dir))

        tokenizer.save_pretrained(str(adapter_dir))

        eval_after: dict[str, Any] = {}

        if tokenized_eval is not None:

            eval_after = trainer.evaluate()

        evaluator = FinetuneEvaluator(
            self._config
        )

        summary = evaluator.build_summary(
            train_result.metrics,
            eval_after,
        )

        evaluator.save_summary(
            output_dir,
            summary,
        )

        report = LoRAExperimentReport.build(
            experiment_name=self._lora_config.experiment_name,
            model_path=self._config.model_path,
            load_in_4bit=self._lora_config.load_in_4bit,
            training_time_seconds=elapsed,
            gpu_memory={
                **memory_after,
                "before": memory_before,
            },
            train_metrics=train_result.metrics,
            eval_before=eval_before,
            eval_after=eval_after,
            adapter_path=str(adapter_dir),
            output_dir=str(output_dir),
            global_step=int(train_result.global_step),
        )

        report_json, report_md = report.save(output_dir)

        logger.info(
            "LoRA finetune done: adapter=%s time=%.2fs",
            adapter_dir,
            elapsed,
        )

        return LoRAFinetuneResult(
            output_dir=output_dir,
            train_loss=train_result.metrics.get(
                "train_loss"
            ),
            eval_loss=eval_after.get("eval_loss"),
            global_step=int(train_result.global_step),
            metrics=summary,
            adapter_dir=adapter_dir,
            report_json=report_json,
            report_markdown=report_md,
            training_time_seconds=elapsed,
            gpu_memory=memory_after,
        )

    def _load_model_with_lora(self):

        import torch
        from peft import LoraConfig
        from peft import get_peft_model
        from transformers import AutoModelForCausalLM

        cfg = self._lora_config

        model_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
        }

        if cfg.load_in_4bit or cfg.load_in_8bit:

            from transformers import BitsAndBytesConfig

            compute_dtype = getattr(
                torch,
                cfg.bnb_4bit_compute_dtype,
                torch.bfloat16,
            )

            model_kwargs["quantization_config"] = (
                BitsAndBytesConfig(
                    load_in_4bit=cfg.load_in_4bit,
                    load_in_8bit=cfg.load_in_8bit,
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
                    bnb_4bit_use_double_quant=cfg.use_double_quant,
                )
            )

            model_kwargs["device_map"] = "auto"

        model = AutoModelForCausalLM.from_pretrained(
            cfg.model_path,
            **model_kwargs,
        )

        if cfg.load_in_4bit or cfg.load_in_8bit:

            from peft import prepare_model_for_kbit_training

            model = prepare_model_for_kbit_training(model)

        target_modules = self._resolve_target_modules(
            cfg.model_path,
            cfg.target_modules,
        )

        lora_config = LoraConfig(
            r=cfg.lora_r,
            lora_alpha=cfg.lora_alpha,
            lora_dropout=cfg.lora_dropout,
            target_modules=target_modules,
            bias=cfg.bias,
            task_type=cfg.task_type,
        )

        return get_peft_model(model, lora_config)

    @staticmethod
    def _resolve_target_modules(
        model_path: str,
        configured: list[str],
    ) -> list[str]:

        lower = model_path.lower()

        if "qwen" in lower:

            return list(configured) or [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ]

        if "gpt2" in lower or "tiny" in lower:

            return ["c_attn", "c_proj", "c_fc"]

        return list(configured)

    @staticmethod
    def _snapshot_memory() -> dict[str, Any]:

        import torch

        payload: dict[str, Any] = {
            "cuda_available": torch.cuda.is_available(),
            "peak_allocated_mib": None,
            "peak_reserved_mib": None,
            "nvidia_smi_used_mib": None,
        }

        if torch.cuda.is_available():

            payload["peak_allocated_mib"] = round(
                torch.cuda.max_memory_allocated()
                / (1024 ** 2),
                2,
            )

            payload["peak_reserved_mib"] = round(
                torch.cuda.max_memory_reserved()
                / (1024 ** 2),
                2,
            )

        payload["nvidia_smi_used_mib"] = (
            _read_nvidia_smi_used_mib()
        )

        return payload


def _read_nvidia_smi_used_mib() -> float | None:

    import shutil
    import subprocess

    if not shutil.which("nvidia-smi"):

        return None

    try:

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    except (OSError, subprocess.SubprocessError):

        return None

    if result.returncode != 0:

        return None

    line = result.stdout.strip().splitlines()[0]

    try:

        return float(line.strip())

    except ValueError:

        return None


def run_lora_finetune(
    config: LoRAFinetuneConfig,
) -> LoRAFinetuneResult:

    return LoRAFineTuneTrainer(config).run()
