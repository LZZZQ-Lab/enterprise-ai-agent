#!/usr/bin/env bash
# 方案 B：固定 cu124 的 torch 2.6 + vLLM 0.10.x（适配 CUDA 12.8 驱动）
#
# 用法:
#   cd backend
#   bash scripts/fix_vllm_cu124.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_ROOT}"

# shellcheck disable=SC1091
source .venv-vllm/bin/activate

export PIP_DEFAULT_TIMEOUT=600
MAX_ROUNDS="${VLLM_FIX_RETRIES:-8}"

install_torch_cu124() {
  pip install \
    --default-timeout=600 \
    --retries 10 \
    --force-reinstall \
    "torch==2.6.0" \
    "torchvision==0.21.0" \
    "torchaudio==2.6.0" \
    --index-url https://download.pytorch.org/whl/cu124
}

echo "=== Step 1: Reinstall PyTorch cu124 (with retries) ==="
for round in $(seq 1 "${MAX_ROUNDS}"); do
  echo "--- torch round ${round}/${MAX_ROUNDS} ---"
  if install_torch_cu124; then
    break
  fi
  if [[ "${round}" -eq "${MAX_ROUNDS}" ]]; then
    echo "ERROR: torch cu124 install failed after ${MAX_ROUNDS} rounds."
    exit 1
  fi
  echo "Retry in 15s ..."
  sleep 15
done

echo
echo "=== Step 2: Verify CUDA ==="
python <<'PY'
import torch
print("torch", torch.__version__)
print("cuda available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
PY

echo
echo "=== Step 3: Install vLLM 0.10.2 ==="
pip uninstall -y vllm 2>/dev/null || true
for round in $(seq 1 "${MAX_ROUNDS}"); do
  echo "--- vllm round ${round}/${MAX_ROUNDS} ---"
  if pip install --default-timeout=600 --retries 10 "vllm==0.10.2"; then
    break
  fi
  if [[ "${round}" -eq "${MAX_ROUNDS}" ]]; then
    echo "ERROR: vllm 0.10.2 install failed."
    exit 1
  fi
  sleep 15
done

echo
echo "=== Step 3b: Pin transformers (vLLM 0.10.x incompatible with transformers 5.x) ==="
pip install --default-timeout=600 "transformers==4.55.4" "tokenizers>=0.21,<0.22" "huggingface-hub>=0.34,<1.0"

echo
python <<'PY'
import torch
import vllm
print("torch", torch.__version__)
print("vllm", vllm.__version__)
print("cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
PY

echo
echo "Fix OK. Next:"
echo "  bash scripts/verify_vllm_env.sh"
echo "  bash scripts/start_vllm_server.sh"
