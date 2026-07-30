#!/usr/bin/env python3
"""
LoRA / QLoRA 微调 Demo（Task 4.2）。

用法：
    pip install -r requirements-finetune.txt
    python -m scripts.lora_finetune_demo
    python -m scripts.lora_finetune_demo --config data/finetune_demo/lora_qwen_config.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


def _resolve_paths(config) -> None:

    if not Path(config.training_data_path).is_absolute():

        config.training_data_path = str(
            (BACKEND_ROOT / config.training_data_path).resolve()
        )

    if not Path(config.output_dir).is_absolute():

        config.output_dir = str(
            (BACKEND_ROOT / config.output_dir).resolve()
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="LoRA/QLoRA finetune demo",
    )

    default_config = (
        BACKEND_ROOT
        / "data"
        / "finetune_demo"
        / "lora_demo_config.json"
    )

    parser.add_argument(
        "--config",
        default=str(default_config),
    )

    args = parser.parse_args()

    from app.finetune.lora.config import LoRAFinetuneConfig
    from app.finetune.lora.trainer import run_lora_finetune

    config = LoRAFinetuneConfig.from_json_file(
        args.config
    )

    _resolve_paths(config)

    result = run_lora_finetune(config)

    print("LoRA finetune finished.")
    print(f"  adapter_dir: {result.adapter_dir}")
    print(f"  training_time_seconds: {result.training_time_seconds:.2f}")
    print(f"  gpu_memory: {result.gpu_memory}")
    print(f"  report: {result.report_markdown}")


if __name__ == "__main__":

    main()
