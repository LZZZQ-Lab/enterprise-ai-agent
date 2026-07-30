"""
Task 2.4: 检查 vLLM 服务与依赖状态。

运行:
    cd backend
    python scripts/check_vllm_service.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version


DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"


def _package_version(name: str) -> str:

    try:

        return version(name)

    except PackageNotFoundError:

        return "NOT INSTALLED"


def _check_gpu() -> None:

    print("=== GPU ===")

    if shutil.which("nvidia-smi") is None:

        print("nvidia-smi : NOT FOUND")
        print()
        return

    try:

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        print(result.stdout.strip())

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:

        print(f"nvidia-smi error: {error}")

    print()


def _check_dependencies() -> None:

    print("=== Dependencies ===")

    for package in ("torch", "vllm", "httpx"):

        print(f"{package:<8}: {_package_version(package)}")

    print()


def _check_vllm_cli() -> None:

    print("=== vLLM CLI ===")

    if shutil.which("vllm") is None:

        print("vllm command : NOT FOUND in PATH")
        print()
        return

    try:

        result = subprocess.run(
            ["vllm", "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )

        output = (result.stdout or result.stderr).strip()
        print(f"vllm command : FOUND ({output})")

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:

        print(f"vllm command : ERROR ({error})")

    print()


def _check_service(base_url: str = DEFAULT_BASE_URL) -> None:

    print("=== vLLM Service ===")
    print(f"Base URL : {base_url}")

    models_url = f"{base_url.rstrip('/')}/models"

    try:

        with urllib.request.urlopen(models_url, timeout=5) as response:

            payload = json.loads(response.read().decode("utf-8"))

        models = [item.get("id") for item in payload.get("data", [])]

        print("Status   : RUNNING")
        print(f"Models   : {', '.join(models) if models else '(none)'}")

    except (urllib.error.URLError, TimeoutError) as error:

        print("Status   : NOT RUNNING")
        print(f"Detail   : {error}")
        print("Hint     : bash scripts/start_vllm_server.sh")

    print()


def main() -> int:

    print()
    print("Enterprise LLM Platform - vLLM Service Status")
    print("=" * 60)
    print()

    _check_gpu()
    _check_dependencies()
    _check_vllm_cli()
    _check_service()

    print("=" * 60)
    return 0


if __name__ == "__main__":

    sys.exit(main())
