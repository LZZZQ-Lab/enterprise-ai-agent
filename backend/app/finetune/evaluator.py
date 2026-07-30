from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.finetune.config import FinetuneConfig


class FinetuneEvaluator:
    """
    训练结果汇总与简单评估指标持久化。
    """

    def __init__(
        self,
        config: FinetuneConfig,
    ) -> None:

        self._config = config

    def build_summary(
        self,
        train_metrics: dict[str, Any],
        eval_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        eval_metrics = eval_metrics or {}

        return {
            "model_path": self._config.model_path,
            "training_data_path": str(
                self._config.resolve_training_path()
            ),
            "batch_size": self._config.batch_size,
            "learning_rate": self._config.learning_rate,
            "seed": self._config.seed,
            "train": dict(train_metrics),
            "eval": dict(eval_metrics),
            "train_loss": train_metrics.get(
                "train_loss"
            ),
            "eval_loss": eval_metrics.get("eval_loss"),
        }

    def save_summary(
        self,
        output_dir: Path,
        summary: dict[str, Any],
    ) -> Path:

        target = output_dir / "eval_summary.json"

        target.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return target

    @staticmethod
    def load_summary(
        output_dir: Path,
    ) -> dict[str, Any]:

        path = output_dir / "eval_summary.json"

        if not path.is_file():

            return {}

        return json.loads(
            path.read_text(encoding="utf-8")
        )
