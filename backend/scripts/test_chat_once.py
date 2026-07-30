#!/usr/bin/env python3
"""One-shot POST /api/v1/chat for local smoke test."""

from __future__ import annotations

import json
import sys

import httpx


def main() -> int:
    url = "http://127.0.0.1:8001/api/v1/chat"
    payload = {
        "session_id": "test-1",
        "message": "你好，请用一句话介绍你自己。",
    }
    response = httpx.post(url, json=payload, timeout=120.0)
    print(response.status_code)
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
