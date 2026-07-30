from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.finetune.config import FinetuneConfig


class FinetuneDatasetBuilder:
    """
    原始数据 → HuggingFace Dataset（文本列 `text`）。

    支持 JSONL，每行一种格式：
    - {"instruction","input","output"}
    - {"messages":[{"role","content"},...]}
    - {"text":"..."}
    """

    def __init__(
        self,
        config: FinetuneConfig,
    ) -> None:

        self._config = config

    def load_raw_records(
        self,
        path: Path | None = None,
    ) -> list[dict[str, Any]]:

        source = path or self._config.resolve_training_path()

        if not source.is_file():

            raise FileNotFoundError(
                f"Training data not found: {source}"
            )

        records: list[dict[str, Any]] = []

        with source.open(
            encoding="utf-8",
        ) as handle:

            for line_number, line in enumerate(
                handle,
                start=1,
            ):

                stripped = line.strip()

                if not stripped:

                    continue

                try:

                    records.append(
                        json.loads(stripped)
                    )

                except json.JSONDecodeError as error:

                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: "
                        f"{error}"
                    ) from error

        if not records:

            raise ValueError(
                f"No training records in {source}"
            )

        return records

    def build_hf_dataset(
        self,
        path: Path | None = None,
    ):
        """
        返回 (train_dataset, eval_dataset | None)。
        """

        from datasets import Dataset

        records = self.load_raw_records(path)

        texts = [
            self.format_record(record)
            for record in records
        ]

        dataset = Dataset.from_dict({"text": texts})

        eval_ratio = self._config.eval_ratio

        if eval_ratio <= 0 or len(texts) < 2:

            return dataset, None

        split = dataset.train_test_split(
            test_size=min(
                eval_ratio,
                max(1 / len(texts), 0.5),
            ),
            seed=self._config.seed,
        )

        return split["train"], split["test"]

    @staticmethod
    def format_record(
        record: dict[str, Any],
    ) -> str:

        if "text" in record:

            return str(record["text"]).strip()

        if "messages" in record:

            parts: list[str] = []

            for message in record["messages"]:

                role = str(
                    message.get("role", "user")
                ).capitalize()

                content = str(
                    message.get("content", "")
                ).strip()

                if content:

                    parts.append(
                        f"### {role}:\n{content}"
                    )

            return "\n\n".join(parts)

        instruction = str(
            record.get("instruction", "")
        ).strip()

        user_input = str(
            record.get("input", "")
        ).strip()

        output = str(
            record.get("output", "")
        ).strip()

        prompt_parts = []

        if instruction:

            prompt_parts.append(instruction)

        if user_input:

            prompt_parts.append(user_input)

        user_block = "\n".join(prompt_parts)

        return (
            f"### User:\n{user_block}\n\n"
            f"### Assistant:\n{output}"
        )
