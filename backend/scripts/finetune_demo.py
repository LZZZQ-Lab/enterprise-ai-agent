#!/usr/bin/env python3
"""
小规模微调 Demo（Task 4.1）。

默认使用 sshleifer/tiny-gpt2 + 企业样例 JSONL，max_steps=8，可在 CPU 上 smoke。

用法（在 backend 目录）：
    pip install -r requirements-finetune.txt
    python -m scripts.finetune_demo
    python -m scripts.finetune_demo --config data/finetune_demo/demo_config.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Enterprise finetune smoke demo",
    )

    default_config = (
        BACKEND_ROOT
        / "data"
        / "finetune_demo"
        / "demo_config.json"
    )

    parser.add_argument(
        "--config",
        default=str(default_config),
        help="FinetuneConfig JSON 路径",
    )

    args = parser.parse_args()

    from app.finetune.config import FinetuneConfig
    from app.finetune.trainer import run_finetune

    config = FinetuneConfig.from_json_file(
        args.config
    )

    if not Path(config.training_data_path).is_absolute():

        config.training_data_path = str(
            (BACKEND_ROOT / config.training_data_path).resolve()
        )

    if not Path(config.output_dir).is_absolute():

        config.output_dir = str(
            (BACKEND_ROOT / config.output_dir).resolve()
        )

    result = run_finetune(config)

    print("Finetune demo finished.")
    print(f"  output_dir: {result.output_dir}")
    print(f"  global_step: {result.global_step}")
    print(f"  train_loss: {result.train_loss}")
    print(f"  eval_loss: {result.eval_loss}")


if __name__ == "__main__":

    main()
