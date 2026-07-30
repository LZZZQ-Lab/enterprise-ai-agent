from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any


@dataclass
class LoRAExperimentReport:
    """
    LoRA/QLoRA 实验报告（显存、耗时、效果）。
    """

    experiment_name: str

    model_path: str

    method: str

    training_time_seconds: float

    gpu_memory: dict[str, Any]

    metrics: dict[str, Any]

    adapter_path: str

    output_dir: str

    created_at: str

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:

        return asdict(self)

    def save(
        self,
        output_dir: Path,
    ) -> tuple[Path, Path]:

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_path = output_dir / "lora_experiment_report.json"

        json_path.write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        md_path = output_dir / "lora_experiment_report.md"

        md_path.write_text(
            self.to_markdown(),
            encoding="utf-8",
        )

        return json_path, md_path

    def to_markdown(self) -> str:

        memory = self.gpu_memory

        metrics = self.metrics

        return (
            f"# LoRA/QLoRA 实验报告\n\n"
            f"- **实验名称**: {self.experiment_name}\n"
            f"- **基座模型**: `{self.model_path}`\n"
            f"- **方法**: {self.method}\n"
            f"- **时间**: {self.created_at}\n"
            f"- **Adapter 路径**: `{self.adapter_path}`\n\n"
            f"## 训练耗时\n\n"
            f"- 总耗时: **{self.training_time_seconds:.2f} s**\n\n"
            f"## 训练显存\n\n"
            f"- CUDA 可用: {memory.get('cuda_available')}\n"
            f"- 峰值 allocated (MiB): "
            f"{memory.get('peak_allocated_mib', 'N/A')}\n"
            f"- 峰值 reserved (MiB): "
            f"{memory.get('peak_reserved_mib', 'N/A')}\n"
            f"- nvidia-smi used (MiB): "
            f"{memory.get('nvidia_smi_used_mib', 'N/A')}\n\n"
            f"## 效果变化\n\n"
            f"- 初始 eval loss: {metrics.get('eval_loss_before', 'N/A')}\n"
            f"- 最终 train loss: {metrics.get('train_loss', 'N/A')}\n"
            f"- 最终 eval loss: {metrics.get('eval_loss_after', 'N/A')}\n"
            f"- Δ eval loss: {metrics.get('eval_loss_delta', 'N/A')}\n"
            f"- 训练步数: {metrics.get('global_step', 'N/A')}\n\n"
            f"## 说明\n\n"
            f"{self.notes or '无'}\n"
        )

    @classmethod
    def build(
        cls,
        *,
        experiment_name: str,
        model_path: str,
        load_in_4bit: bool,
        training_time_seconds: float,
        gpu_memory: dict[str, Any],
        train_metrics: dict[str, Any],
        eval_before: dict[str, Any] | None,
        eval_after: dict[str, Any] | None,
        adapter_path: str,
        output_dir: str,
        global_step: int,
    ) -> LoRAExperimentReport:

        eval_before_loss = (
            eval_before.get("eval_loss")
            if eval_before
            else None
        )

        eval_after_loss = (
            eval_after.get("eval_loss")
            if eval_after
            else None
        )

        delta = None

        if (
            eval_before_loss is not None
            and eval_after_loss is not None
        ):

            delta = eval_after_loss - eval_before_loss

        method = "QLoRA (4bit)" if load_in_4bit else "LoRA"

        return cls(
            experiment_name=experiment_name,
            model_path=model_path,
            method=method,
            training_time_seconds=training_time_seconds,
            gpu_memory=gpu_memory,
            metrics={
                "train_loss": train_metrics.get("train_loss"),
                "eval_loss_before": eval_before_loss,
                "eval_loss_after": eval_after_loss,
                "eval_loss_delta": delta,
                "global_step": global_step,
            },
            adapter_path=adapter_path,
            output_dir=output_dir,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=(
                "Qwen2.5 推荐使用本流程；"
                "接入推理时加载 adapter 或 merge 后部署 vLLM。"
            ),
        )
