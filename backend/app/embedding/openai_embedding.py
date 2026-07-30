from __future__ import annotations

from openai import OpenAI

from app.config.settings import get_settings
from app.embedding.base import BaseEmbedding


class OpenAIEmbedding(BaseEmbedding):
    """
    OpenAI 兼容 Embedding API。

    支持官方 OpenAI 及 OPENAI_BASE_URL 指向的兼容网关。
    """

    _DEFAULT_MODEL = "text-embedding-3-small"
    _DEFAULT_DIMENSION = 1536

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
    ) -> None:

        app_settings = get_settings()

        self._model = (
            model
            or app_settings.EMBEDDING_MODEL
            or self._DEFAULT_MODEL
        )

        self._dimension = (
            dimension
            if dimension is not None
            else (
                app_settings.EMBEDDING_DIMENSION
                if app_settings.EMBEDDING_DIMENSION > 0
                else self._DEFAULT_DIMENSION
            )
        )

        self._client = OpenAI(
            api_key=(
                api_key
                if api_key is not None
                else app_settings.API_KEY
            ),
            base_url=(
                base_url
                if base_url is not None
                else app_settings.OPENAI_BASE_URL
            ),
        )

    @property
    def dimension(self) -> int:

        return self._dimension

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:

            return []

        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
        )

        ordered = sorted(
            response.data,
            key=lambda item: item.index,
        )

        return [item.embedding for item in ordered]
