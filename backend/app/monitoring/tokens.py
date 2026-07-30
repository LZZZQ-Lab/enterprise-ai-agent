"""Token 估算（无 usage 字段时的近似值）。"""

from __future__ import annotations

import re


def estimate_token_count(text: str) -> int:

    if not text:

        return 0

    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = max(0, len(text) - cjk)

    return max(1, int(cjk * 1.2 + other / 4))
