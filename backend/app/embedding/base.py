from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class BaseEmbedding(ABC):
    """
    统一 Embedding 抽象。

    RAG 与其它模块只依赖本接口；具体 OpenAI / 本地模型由 factory 注入。
    """

    @abstractmethod
    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        将一批文本转换为 embedding 向量。

        返回顺序与输入 texts 一致；空字符串对应零向量或模型约定向量。
        """

        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        向量维度，供 VectorStore 校验使用。
        """

        pass

    def embed_one(
        self,
        text: str,
    ) -> list[float]:
        """
        单条文本便捷方法，内部调用 embed([text])。
        """

        vectors = self.embed([text])

        if not vectors:

            return []

        return vectors[0]
