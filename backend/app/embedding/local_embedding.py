from __future__ import annotations

from typing import Any

from app.config.settings import get_settings
from app.embedding.base import BaseEmbedding


class LocalEmbedding(BaseEmbedding):
    """
    本地 Embedding 模型（预留 / 可选依赖）。

    需安装 sentence-transformers；未安装时在首次 embed 给出明确错误。
    模型 ID 由 EMBEDDING_MODEL 或 LOCAL_EMBEDDING_MODEL_ID 配置。
    """

    def __init__(
        self,
        model_id: str | None = None,
        device: str | None = None,
    ) -> None:

        app_settings = get_settings()

        self._model_id = (
            model_id
            or app_settings.EMBEDDING_MODEL
            or app_settings.LOCAL_EMBEDDING_MODEL_ID
        )

        self._device = device or app_settings.LOCAL_EMBEDDING_DEVICE

        self._model: Any = None
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:

        self._ensure_model()

        assert self._dimension is not None

        return self._dimension

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:

            return []

        self._ensure_model()

        assert self._model is not None

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return vectors.tolist()

    def _ensure_model(self) -> None:

        if self._model is not None:

            return

        try:

            from sentence_transformers import SentenceTransformer

        except ImportError as error:

            raise RuntimeError(
                "Local embedding requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            ) from error

        self._model = SentenceTransformer(
            self._model_id,
            device=self._device,
        )

        sample = self._model.encode(
            ["dimension probe"],
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        self._dimension = int(sample.shape[1])
