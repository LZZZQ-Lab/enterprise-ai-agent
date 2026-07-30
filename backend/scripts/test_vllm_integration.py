"""
Task 2.5: 验证 Platform VLLMProvider 与 vLLM 服务对接。

真实 vLLM 联调（需先启动服务）:
    bash scripts/start_vllm_server.sh
    python scripts/test_vllm_integration.py

开发联调（Mock OpenAI 响应，无需 vLLM 进程）:
    python scripts/test_vllm_integration.py --mock-client

Live 服务检测:
    python scripts/test_vllm_integration.py --live
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Verify Platform VLLMProvider integration.",
    )

    parser.add_argument(
        "--base-url",
        default=os.environ.get("VLLM_ENDPOINT", "http://127.0.0.1:8000/v1"),
        help="vLLM OpenAI API base URL",
    )

    parser.add_argument(
        "--mock-client",
        action="store_true",
        help="Mock vLLM HTTP responses (no running server required)",
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Require live vLLM at VLLM_ENDPOINT before testing",
    )

    return parser.parse_args()


def _service_running(base_url: str) -> bool:

    models_url = f"{base_url.rstrip('/')}/models"

    try:

        with urllib.request.urlopen(models_url, timeout=3) as response:

            return response.status == 200

    except (urllib.error.URLError, TimeoutError):

        return False


def _configure_provider_env(base_url: str) -> None:

    os.environ["MODEL_PROVIDER"] = "vllm"
    os.environ["VLLM_ENDPOINT"] = base_url.rstrip("/")
    os.environ.setdefault("MODEL_NAME", "Qwen2.5")
    os.environ.setdefault("VLLM_API_KEY", "EMPTY")

    from app.config.settings import reset_settings_cache
    from app.llm.factory import reset_llm_client_cache

    reset_settings_cache()
    reset_llm_client_cache()


def _run_chat_test(*, use_mock_client: bool) -> int:

    from app.llm.factory import create_llm_provider
    from app.llm.types import Message
    from app.llm.vllm_provider import VLLMProvider

    provider = create_llm_provider("vllm")

    if not isinstance(provider, VLLMProvider):

        print(f"ERROR: expected VLLMProvider, got {type(provider).__name__}")
        return 1

    print(f"Provider      : {type(provider).__name__}")
    print(f"Model ID      : {provider.model_id}")
    print(f"Endpoint      : {provider.endpoint}")
    print()

    if use_mock_client:

        mock_response = SimpleNamespace(
            model=provider.model_id,
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="你好，我是 Qwen vLLM 助手（Mock Client）。",
                        tool_calls=None,
                    )
                )
            ],
        )

        provider.client = MagicMock()
        provider.client.chat.completions.create.return_value = mock_response
        print("Mode          : mock-client (offline)")
    else:

        print("Mode          : live vLLM HTTP")

    print("Calling VLLMProvider.chat() ...")
    print()

    try:

        result = provider.chat(
            [Message(role="user", content="你好，请用一句话介绍自己")],
            use_tools=False,
        )

    except Exception as error:

        print(f"ERROR: {error}")
        return 1

    print("-" * 60)
    print("Agent LLM Answer:")
    print(result.content or "(empty)")
    print("-" * 60)
    print(f"Model         : {result.model}")
    print("Status        : OK")
    print("=" * 60)

    return 0 if result.content else 1


def main() -> int:

    args = _parse_args()
    base_url = args.base_url.rstrip("/")

    print("=" * 60)
    print("Task 2.5 Platform <-> vLLM Integration")
    print("=" * 60)
    print(f"VLLM_ENDPOINT : {base_url}")
    print()

    if args.mock_client:

        _configure_provider_env(base_url)
        return _run_chat_test(use_mock_client=True)

    if args.live or not _service_running(base_url):

        if not _service_running(base_url):

            print("Live vLLM not reachable.")
            if "127.0.0.1" in base_url or "localhost" in base_url:
                print()
                print("WSL mirrored networking: try LAN IP instead of 127.0.0.1:")
                print("  bash scripts/probe_vllm_localhost.sh")
                print("  # then set VLLM_ENDPOINT in .env or:")
                print("  python scripts/test_vllm_integration.py --live \\")
                print('    --base-url "http://<WSL-IP>:8000/v1"')
                print("  # WSL-IP: hostname -I | awk '{print $1}'")
            print()
            print("Quick offline check:")
            print("  python scripts/test_vllm_integration.py --mock-client")
            print()
            print("Real vLLM in WSL (see docs/vllm_deployment.md):")
            print("  bash scripts/start_vllm_server.sh")
            print("  python scripts/test_vllm_integration.py --live")
            return 1

    _configure_provider_env(base_url)
    return _run_chat_test(use_mock_client=False)


if __name__ == "__main__":

    sys.exit(main())
