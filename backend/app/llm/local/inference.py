from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings
from app.core.logger import logger
from app.llm.local.model_loader import ModelLoader
from app.llm.local.tokenizer import build_qwen_prompt

if TYPE_CHECKING:
    from app.llm.types import Message


class Inference:
    """
    本地 Transformers 推理引擎。

    输入 messages，输出模型文本回答。
    """

    def __init__(
        self,
        loader: ModelLoader | None = None,
    ) -> None:

        self._loader = loader or ModelLoader.from_settings()

    @property
    def model_id(self) -> str:

        return self._loader.model_id

    def generate(
        self,
        messages: list[Message],
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        执行 Qwen2.5-Instruct 本地推理。
        """

        import torch

        loaded = self._loader.ensure_loaded()
        prompt = build_qwen_prompt(
            loaded.tokenizer,
            messages,
        )

        inputs = loaded.tokenizer(
            prompt,
            return_tensors="pt",
        )

        model_device = self._resolve_input_device(loaded.model)
        inputs = {key: value.to(model_device) for key, value in inputs.items()}

        max_tokens = max_new_tokens or settings.LOCAL_MODEL_MAX_NEW_TOKENS
        temp = (
            temperature
            if temperature is not None
            else settings.TEMPERATURE
        )

        generate_kwargs: dict = {
            "max_new_tokens": max_tokens,
            "do_sample": temp > 0,
            "pad_token_id": loaded.tokenizer.eos_token_id,
            "eos_token_id": loaded.tokenizer.eos_token_id,
        }

        if temp > 0:

            generate_kwargs["temperature"] = temp

        logger.info(
            "Local inference: model=%s max_new_tokens=%s temperature=%s",
            loaded.model_id,
            max_tokens,
            temp,
        )

        with torch.inference_mode():

            output_ids = loaded.model.generate(
                **inputs,
                **generate_kwargs,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
        answer = loaded.tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip()

        return answer

    @staticmethod
    def _resolve_input_device(model):

        import torch

        if hasattr(model, "device"):

            return torch.device(model.device)

        if hasattr(model, "hf_device_map"):

            first_device = next(iter(model.hf_device_map.values()))

            return torch.device(first_device)

        return torch.device("cpu")
