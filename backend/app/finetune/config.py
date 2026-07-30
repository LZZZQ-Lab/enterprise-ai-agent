from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any


@dataclass
class FinetuneConfig:
    """
    微调训练配置（与 Agent / 业务解耦）。

    可通过 CLI、YAML 或环境变量构造；训练产物写入 output_dir。
    """

    training_data_path: str

    model_path: str

    output_dir: str = "./artifacts/finetune/run"

    batch_size: int = 2

    learning_rate: float = 2e-5

    num_train_epochs: float = 1.0

    max_steps: int = -1

    max_seq_length: int = 512

    warmup_ratio: float = 0.0

    weight_decay: float = 0.0

    seed: int = 42

    logging_steps: int = 5

    save_steps: int = 50

    eval_ratio: float = 0.1

    bf16: bool = False

    fp16: bool = False

    gradient_accumulation_steps: int = 1

    extra: dict[str, Any] = field(default_factory=dict)

    def resolve_training_path(self) -> Path:

        return Path(self.training_data_path).expanduser().resolve()

    def resolve_output_dir(self) -> Path:

        return Path(self.output_dir).expanduser().resolve()

    def to_dict(self) -> dict[str, Any]:

        payload = asdict(self)

        payload["training_data_path"] = str(
            self.resolve_training_path()
        )

        payload["output_dir"] = str(
            self.resolve_output_dir()
        )

        return payload

    def save_json(
        self,
        path: Path | None = None,
    ) -> Path:

        target = path or (
            self.resolve_output_dir() / "finetune_config.json"
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return target

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> FinetuneConfig:

        known = {
            field_name
            for field_name in cls.__dataclass_fields__
        }

        core = {
            key: value
            for key, value in data.items()
            if key in known and key != "extra"
        }

        extra = dict(data.get("extra") or {})

        for key, value in data.items():

            if key not in known:

                extra[key] = value

        core["extra"] = extra

        return cls(**core)

    @classmethod
    def from_json_file(
        cls,
        path: str | Path,
    ) -> FinetuneConfig:

        loaded = json.loads(
            Path(path).read_text(encoding="utf-8")
        )

        return cls.from_dict(loaded)
