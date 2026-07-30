"""
Prompt / Embedding / Response 三层缓存。
"""

from __future__ import annotations

import json

from app.cache.base import CacheStore
from app.cache.keys import cache_key
from app.cache.stats import record_hit
from app.cache.stats import record_miss
from app.cache.stats import record_set
from app.cache.types import CacheLayer
from app.llm.types import ChatResult
from app.llm.types import Message


class PromptCache:
    """缓存规范化 Prompt（messages JSON）。"""

    def __init__(
        self,
        store: CacheStore,
        *,
        ttl_seconds: int = 86400,
    ) -> None:
        self._store = store
        self._ttl = ttl_seconds

    def get(
        self,
        *,
        model: str,
        messages: list[Message],
    ) -> list[dict] | None:
        key = self._make_key(model=model, messages=messages)
        raw = self._store.get(key)
        if raw is None:
            record_miss(CacheLayer.PROMPT)
            return None
        record_hit(CacheLayer.PROMPT)
        return json.loads(raw.decode("utf-8"))

    def set(
        self,
        *,
        model: str,
        messages: list[Message],
        payload: list[dict],
    ) -> None:
        key = self._make_key(model=model, messages=messages)
        self._store.set(
            key,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ttl_seconds=self._ttl,
        )
        record_set(CacheLayer.PROMPT)

    def _make_key(self, *, model: str, messages: list[Message]) -> str:
        body = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
        }
        return cache_key(CacheLayer.PROMPT.value, body)


class EmbeddingCache:
    """按文本 + 模型维度缓存向量。"""

    def __init__(
        self,
        store: CacheStore,
        *,
        ttl_seconds: int = 604800,
        model: str = "",
        dimension: int = 0,
    ) -> None:
        self._store = store
        self._ttl = ttl_seconds
        self._model = model
        self._dimension = dimension

    def get_many(
        self,
        texts: list[str],
    ) -> list[list[float] | None]:
        results: list[list[float] | None] = []
        for text in texts:
            key = self._make_key(text)
            raw = self._store.get(key)
            if raw is None:
                record_miss(CacheLayer.EMBEDDING)
                results.append(None)
            else:
                record_hit(CacheLayer.EMBEDDING)
                results.append(json.loads(raw.decode("utf-8")))
        return results

    def set_many(
        self,
        texts: list[str],
        vectors: list[list[float]],
    ) -> None:
        for text, vector in zip(texts, vectors, strict=True):
            key = self._make_key(text)
            self._store.set(
                key,
                json.dumps(vector).encode("utf-8"),
                ttl_seconds=self._ttl,
            )
            record_set(CacheLayer.EMBEDDING)

    def _make_key(self, text: str) -> str:
        return cache_key(
            CacheLayer.EMBEDDING.value,
            {
                "model": self._model,
                "dimension": self._dimension,
                "text": text,
            },
        )


class ResponseCache:
    """缓存 LLM 文本响应（无 tool_calls 时）。"""

    def __init__(
        self,
        store: CacheStore,
        *,
        ttl_seconds: int = 3600,
    ) -> None:
        self._store = store
        self._ttl = ttl_seconds

    def get(
        self,
        *,
        model: str,
        messages: list[Message],
        use_tools: bool,
    ) -> ChatResult | None:
        if use_tools:
            record_miss(CacheLayer.RESPONSE)
            return None

        key = self._make_key(model=model, messages=messages)
        raw = self._store.get(key)
        if raw is None:
            record_miss(CacheLayer.RESPONSE)
            return None

        record_hit(CacheLayer.RESPONSE)
        payload = json.loads(raw.decode("utf-8"))
        return ChatResult.model_validate(payload)

    def set(
        self,
        *,
        model: str,
        messages: list[Message],
        result: ChatResult,
    ) -> None:
        if result.tool_calls:
            return

        key = self._make_key(model=model, messages=messages)
        self._store.set(
            key,
            result.model_dump_json().encode("utf-8"),
            ttl_seconds=self._ttl,
        )
        record_set(CacheLayer.RESPONSE)

    def _make_key(self, *, model: str, messages: list[Message]) -> str:
        body = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
        }
        return cache_key(CacheLayer.RESPONSE.value, body)
