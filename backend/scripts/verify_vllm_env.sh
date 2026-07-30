#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck disable=SC1091
source "${BACKEND_ROOT}/.venv-vllm/bin/activate"
python <<'PY'
import torch
import vllm
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    try:
        print("gpu", torch.cuda.get_device_name(0))
    except RuntimeError as e:
        print("gpu_name_error", e)
print("vllm", vllm.__version__)
PY
vllm --version
