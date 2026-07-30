"""
Task 2.2 本地 Qwen2.5 推理验证脚本。

运行:
    cd backend
    python scripts/test_local_llm.py

可选:
    python scripts/test_local_llm.py --model-id Qwen/Qwen2.5-0.5B-Instruct
    python scripts/test_local_llm.py --prompt "你好，请介绍一下自己"
"""

from __future__ import annotations

import argparse
import sys
import time


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Test local Qwen2.5 inference via LocalProvider.",
    )

    parser.add_argument(
        "--model-id",
        default=None,
        help="HuggingFace model id (default: settings.LOCAL_MODEL_ID)",
    )

    parser.add_argument(
        "--prompt",
        default="你好，请介绍一下自己",
        help="User prompt for the test",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=None,
        help="Override max new tokens",
    )

    return parser.parse_args()


def main() -> int:

    args = _parse_args()

    try:

        import torch

    except ImportError:

        print("ERROR: PyTorch is not installed.")
        print("Install: pip install torch --index-url https://download.pytorch.org/whl/cu124")
        return 1

    try:

        from transformers import AutoTokenizer

    except ImportError:

        print("ERROR: transformers is not installed.")
        print("Install: pip install -r requirements-llm.txt")
        return 1

    _ = torch, AutoTokenizer

    from app.llm.local_provider import LocalProvider
    from app.llm.types import Message

    print("=" * 60)
    print("Task 2.2 Local LLM Test")
    print("=" * 60)
    print(f"PyTorch     : {torch.__version__}")
    print(f"CUDA        : {torch.cuda.is_available()}")
    print(f"Prompt      : {args.prompt}")
    print()

    provider_kwargs = {}

    if args.model_id:

        provider_kwargs["model_id"] = args.model_id

    provider = LocalProvider(**provider_kwargs)

    print(f"Model ID    : {provider.model_id}")
    print("Loading model and running inference...")
    print()

    started = time.perf_counter()

    result = provider.chat(
        [
            Message(
                role="user",
                content=args.prompt,
            )
        ],
        use_tools=False,
    )

    elapsed = time.perf_counter() - started

    print("-" * 60)
    print("Model Answer:")
    print(result.content or "")
    print("-" * 60)
    print(f"Model       : {result.model}")
    print(f"Elapsed     : {elapsed:.2f}s")
    print("=" * 60)

    if not result.content:

        print("ERROR: empty model response")
        return 1

    return 0


if __name__ == "__main__":

    sys.exit(main())
