"""OpenAI-compatible chat completion streaming client for benchmarks."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from benchmark.common import Timer
from benchmark.common import estimate_token_count
from benchmark.common import parse_sse_data_lines


def resolve_openai_config(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str, str, str]:
    url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip(
        "/"
    )
    key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
    resolved_model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    return url, key, resolved_model


def resolve_model_from_api(base_url: str, timeout: int, api_key: str | None = None) -> str:
    url = f"{base_url.rstrip('/')}/models"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = data.get("data") or []
    if not items:
        raise RuntimeError("No models from /v1/models")
    return items[0]["id"]


def run_chat_stream_once(
    *,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
    api_key: str | None = None,
) -> tuple[float, float, int]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        method="POST",
        headers=headers,
    )
    timer = Timer()
    ttft_ms: float | None = None
    chunks: list[str] = []
    completion_tokens = 0

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            for event in parse_sse_data_lines(raw):
                choices = event.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content") or ""
                    if piece and ttft_ms is None:
                        ttft_ms = timer.elapsed_ms()
                    if piece:
                        chunks.append(piece)
                usage = event.get("usage")
                if usage and usage.get("completion_tokens"):
                    completion_tokens = int(usage["completion_tokens"])

    total_ms = timer.elapsed_ms()
    text = "".join(chunks)
    if completion_tokens <= 0:
        completion_tokens = estimate_token_count(text)
    if ttft_ms is None:
        ttft_ms = total_ms
    return ttft_ms, total_ms, completion_tokens
