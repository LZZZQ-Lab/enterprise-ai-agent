from __future__ import annotations

from app.config.settings import get_settings
from app.core.logger import logger
from app.llm.base import BaseLLM
from app.llm.local.inference import Inference
from app.llm.types import ChatResult
from app.llm.types import Message


class LocalLLMProvider(BaseLLM):
    """
    本地 LLM Provider（Task 2.3）。

    实现 BaseLLM.chat()，内部委托 app.llm.local.Inference 完成 Qwen 推理。
    Agent 仅通过 get_llm_client() 调用，不直接接触 transformers。
    """

    def __init__(
        self,
        *,
        model_id: str | None = None,
        inference: Inference | None = None,
    ) -> None:

        super().__init__()

        resolved_model_id = (
            model_id or get_settings().resolve_model_info().model_id
        )

        if inference is not None:

            self._inference = inference

        else:

            from app.llm.local.model_loader import ModelLoader

            loader = ModelLoader(model_id=resolved_model_id)
            self._inference = Inference(loader=loader)

        self.model_id = self._inference.model_id

        logger.info(
            "LocalLLMProvider initialized: model_id=%s provider=local",
            self.model_id,
        )

    def chat(
        self,
        messages: list[Message],
        use_tools: bool = True,
    ) -> ChatResult:
        """
        统一 LLM 接口：输入 messages，返回 ChatResult。
        """

        if use_tools and self._get_tool_schemas():

            logger.warning(
                "LocalLLMProvider does not support native tool calling yet; "
                "tools are ignored for this request."
            )

        content = self._inference.generate(messages)

        return ChatResult(
            model=self.model_id,
            content=content,
        )


LocalProvider = LocalLLMProvider

__all__ = ["LocalLLMProvider", "LocalProvider"]
