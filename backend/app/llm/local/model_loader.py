from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.config import settings
from app.core.logger import logger


@dataclass
class LoadedModel:
    model: Any
    tokenizer: Any
    device: str
    model_id: str


class ModelLoader:
    """
    负责加载 Qwen2.5 模型、Tokenizer，并管理 device。

    单例懒加载，避免重复占用显存。
    """

    _instances: dict[str, ModelLoader] = {}
    _lock = Lock()

    def __init__(
        self,
        *,
        model_id: str | None = None,
        device: str | None = None,
        load_in_4bit: bool | None = None,
        trust_remote_code: bool = True,
    ) -> None:

        self.model_id = model_id or settings.LOCAL_MODEL_ID
        self.device_preference = device or settings.LOCAL_MODEL_DEVICE
        self.load_in_4bit = (
            settings.LOCAL_MODEL_4BIT
            if load_in_4bit is None
            else load_in_4bit
        )
        self.trust_remote_code = trust_remote_code
        self._loaded: LoadedModel | None = None
        self._load_lock = Lock()

    @classmethod
    def from_settings(cls) -> ModelLoader:
        """
        按当前 Settings 获取（或创建）ModelLoader 单例。
        """

        model_id = settings.LOCAL_MODEL_ID

        with cls._lock:

            if model_id not in cls._instances:

                cls._instances[model_id] = cls(model_id=model_id)

            return cls._instances[model_id]

    @classmethod
    def reset_cache(cls) -> None:
        """测试或切换模型时释放缓存。"""

        with cls._lock:

            cls._instances.clear()

    @property
    def device(self) -> str:

        loaded = self.ensure_loaded()

        return loaded.device

    @property
    def tokenizer(self):

        return self.ensure_loaded().tokenizer

    @property
    def model(self):

        return self.ensure_loaded().model

    def ensure_loaded(self) -> LoadedModel:
        """
        懒加载模型与 Tokenizer。
        """

        if self._loaded is not None:

            return self._loaded

        with self._load_lock:

            if self._loaded is not None:

                return self._loaded

            self._loaded = self._load_model()

            return self._loaded

    def _resolve_device(self) -> str:

        import torch

        preference = (self.device_preference or "auto").lower()

        if preference == "cpu":

            return "cpu"

        if preference == "cuda":

            if not torch.cuda.is_available():

                raise RuntimeError(
                    "LOCAL_MODEL_DEVICE=cuda but CUDA is not available."
                )

            return "cuda"

        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self) -> LoadedModel:

        import torch
        from transformers import AutoModelForCausalLM
        from transformers import AutoTokenizer

        device = self._resolve_device()

        logger.info(
            "Loading local model: id=%s device=%s 4bit=%s",
            self.model_id,
            device,
            self.load_in_4bit,
        )

        tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=self.trust_remote_code,
        )

        model_kwargs: dict[str, Any] = {
            "trust_remote_code": self.trust_remote_code,
        }

        if device == "cuda":

            if self.load_in_4bit and self._can_use_4bit():

                model_kwargs["device_map"] = "auto"
                model_kwargs["load_in_4bit"] = True

            else:

                model_kwargs["torch_dtype"] = torch.float16
                model_kwargs["device_map"] = "auto"

        else:

            model_kwargs["torch_dtype"] = torch.float32
            model_kwargs["device_map"] = "cpu"

        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            **model_kwargs,
        )

        if device == "cpu":

            model = model.to("cpu")

        logger.info(
            "Local model loaded: id=%s device=%s",
            self.model_id,
            device,
        )

        return LoadedModel(
            model=model,
            tokenizer=tokenizer,
            device=device,
            model_id=self.model_id,
        )

    @staticmethod
    def _can_use_4bit() -> bool:

        try:

            import bitsandbytes  # noqa: F401

            return True

        except ImportError:

            logger.info(
                "bitsandbytes not installed; falling back to fp16 loading."
            )

            return False
