from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from app.finetune.config import FinetuneConfig


def default_qwen_target_modules() -> list[str]:

    return [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]


@dataclass
class LoRAFinetuneConfig(FinetuneConfig):
    """
    LoRA / QLoRA 微调配置（扩展 Task 4.1 FinetuneConfig）。
    """

    lora_r: int = 8

    lora_alpha: int = 16

    lora_dropout: float = 0.05

    target_modules: list[str] = field(
        default_factory=default_qwen_target_modules
    )

    bias: str = "none"

    task_type: str = "CAUSAL_LM"

    load_in_4bit: bool = True

    load_in_8bit: bool = False

    bnb_4bit_compute_dtype: str = "bfloat16"

    bnb_4bit_quant_type: str = "nf4"

    use_double_quant: bool = True

    experiment_name: str = "lora_run"

    def resolve_lora_output_dir(self) -> str:

        base = self.resolve_output_dir()

        return str(base / "adapter")

    def to_dict(self) -> dict[str, Any]:

        payload = super().to_dict()

        payload["lora"] = {
            "r": self.lora_r,
            "alpha": self.lora_alpha,
            "dropout": self.lora_dropout,
            "target_modules": list(self.target_modules),
            "bias": self.bias,
            "task_type": self.task_type,
            "load_in_4bit": self.load_in_4bit,
            "load_in_8bit": self.load_in_8bit,
        }

        payload["experiment_name"] = self.experiment_name

        return payload

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> LoRAFinetuneConfig:

        raw = dict(data)

        lora_block = dict(raw.pop("lora", {}) or {})

        experiment_name = raw.pop(
            "experiment_name",
            "lora_run",
        )

        base = FinetuneConfig.from_dict(raw)

        base_fields = {
            name: getattr(base, name)
            for name in base.__dataclass_fields__
        }

        return cls(
            **base_fields,
            lora_r=int(lora_block.get("r", 8)),
            lora_alpha=int(lora_block.get("alpha", 16)),
            lora_dropout=float(
                lora_block.get("dropout", 0.05)
            ),
            target_modules=list(
                lora_block.get(
                    "target_modules",
                    default_qwen_target_modules(),
                )
            ),
            bias=str(lora_block.get("bias", "none")),
            task_type=str(
                lora_block.get("task_type", "CAUSAL_LM")
            ),
            load_in_4bit=bool(
                lora_block.get("load_in_4bit", True)
            ),
            load_in_8bit=bool(
                lora_block.get("load_in_8bit", False)
            ),
            experiment_name=str(experiment_name),
        )

    @classmethod
    def from_json_file(
        cls,
        path: str | Path,
    ) -> LoRAFinetuneConfig:

        loaded = json.loads(
            Path(path).read_text(encoding="utf-8")
        )

        return cls.from_dict(loaded)
