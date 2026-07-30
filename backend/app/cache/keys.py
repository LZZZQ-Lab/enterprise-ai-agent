"""
缓存 Key 生成。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def cache_key(namespace: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"model_cache:{namespace}:{digest}"
