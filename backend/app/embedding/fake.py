import hashlib
import struct

from app.embedding.base import BaseEmbedding


class FakeEmbedding(BaseEmbedding):
    """
    测试用 Embedding 实现。

    基于文本哈希生成确定性向量，不依赖外部 API。
    """

    def __init__(
        self,
        dimension: int = 128,
    ) -> None:

        self._dimension = dimension

    @property
    def dimension(self) -> int:

        return self._dimension

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        return [self._embed_single(text) for text in texts]

    def _embed_single(
        self,
        text: str,
    ) -> list[float]:

        if not text:

            return [0.0] * self._dimension

        seed = hashlib.sha256(
            text.encode("utf-8")
        ).digest()

        vector: list[float] = []

        while len(vector) < self._dimension:

            chunk = seed + struct.pack(
                "<I",
                len(vector),
            )

            seed = hashlib.sha256(chunk).digest()

            for index in range(
                0,
                len(seed),
                4,
            ):

                if len(vector) >= self._dimension:

                    break

                value = struct.unpack(
                    "<I",
                    seed[index:index + 4],
                )[0]

                normalized = (value / 4294967295.0) * 2 - 1

                vector.append(normalized)

        return vector
