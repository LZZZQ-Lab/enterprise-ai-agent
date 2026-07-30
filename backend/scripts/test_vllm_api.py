"""
Task 2.4: 验证 vLLM OpenAI Compatible API。

检查 /v1/models 与 /v1/chat/completions。

运行:
    cd backend
    python scripts/test_vllm_api.py

可选:
    python scripts/test_vllm_api.py --base-url http://127.0.0.1:8000/v1
    python scripts/test_vllm_api.py --prompt "你好，请介绍一下自己"
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Verify vLLM /v1/chat/completions endpoint.",
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/v1",
        help="vLLM OpenAI API base URL",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Model name (default: first model from /v1/models)",
    )

    parser.add_argument(
        "--prompt",
        default="你好，请介绍一下自己",
        help="Test user message",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout seconds",
    )

    return parser.parse_args()


def _http_json(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    timeout: int,
) -> dict:

    data = None

    if payload is not None:

        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:

        return json.loads(response.read().decode("utf-8"))


def _resolve_model(base_url: str, model: str | None, timeout: int) -> str:

    if model:

        return model

    models_url = f"{base_url.rstrip('/')}/models"
    result = _http_json("GET", models_url, timeout=timeout)

    items = result.get("data", [])

    if not items:

        raise RuntimeError("No models returned from /v1/models")

    return items[0]["id"]


def main() -> int:

    args = _parse_args()
    base_url = args.base_url.rstrip("/")

    print("=" * 60)
    print("Task 2.4 vLLM API Verification")
    print("=" * 60)
    print(f"Base URL : {base_url}")
    print(f"Prompt   : {args.prompt}")
    print()

    try:

        model = _resolve_model(base_url, args.model, args.timeout)

        print(f"Model    : {model}")
        print("Calling POST /v1/chat/completions ...")
        print()

        result = _http_json(
            "POST",
            f"{base_url}/chat/completions",
            {
                "model": model,
                "messages": [
                    {"role": "user", "content": args.prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 256,
            },
            timeout=args.timeout,
        )

    except urllib.error.URLError as error:

        print(f"ERROR: cannot reach vLLM server at {base_url}")
        print(f"Detail: {error}")
        print()
        print("Start server first:")
        print("  bash scripts/start_vllm_server.sh")
        return 1

    except Exception as error:

        print(f"ERROR: {error}")
        return 1

    content = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    print("-" * 60)
    print("Model Answer:")
    print(content or "(empty)")
    print("-" * 60)
    print("Status   : OK")
    print("=" * 60)

    if not content:

        return 1

    return 0


if __name__ == "__main__":

    sys.exit(main())
