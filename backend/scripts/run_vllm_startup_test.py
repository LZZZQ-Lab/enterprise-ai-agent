"""Wait for vLLM /v1/models then run API + integration tests."""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000/v1"
MAX_WAIT_SEC = 900
POLL_SEC = 15


def models_up() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/models", timeout=8) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def main() -> int:
    print("Waiting for vLLM at", BASE_URL, f"(max {MAX_WAIT_SEC}s)...")
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        if models_up():
            print("vLLM is UP.")
            break
        print("  not ready, retry in", POLL_SEC, "s")
        time.sleep(POLL_SEC)
    else:
        print("TIMEOUT: vLLM did not become ready.")
        print("Check WSL: tail -50 /tmp/vllm_server.log")
        return 1

    for script in ("scripts/test_vllm_api.py", "scripts/test_vllm_integration.py"):
        cmd = [sys.executable, str(BACKEND / script)]
        if script.endswith("integration.py"):
            cmd.append("--live")
        print("\n>>>", " ".join(cmd))
        result = subprocess.run(cmd, cwd=BACKEND)
        if result.returncode != 0:
            return result.returncode

    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
