#!/usr/bin/env bash
# 下载 vLLM 默认小模型权重（WSL / Linux，可用 hf-mirror）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

if [[ -f "${BACKEND_ROOT}/.venv-vllm/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${BACKEND_ROOT}/.venv-vllm/bin/activate"
fi

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
unset HF_HUB_OFFLINE

if ! command -v huggingface-cli >/dev/null 2>&1; then
  echo "Installing huggingface_hub CLI..."
  pip install -q "huggingface_hub>=0.23.0"
fi

echo "Downloading: ${MODEL}"
echo "HF_ENDPOINT=${HF_ENDPOINT}"
echo "(This is ~1GB; keep network stable.)"
echo

if command -v hf >/dev/null 2>&1; then
  hf download "${MODEL}"
else
  huggingface-cli download "${MODEL}"
fi

echo
echo "Verifying weights..."
export VLLM_MODEL="${MODEL}"
bash "${SCRIPT_DIR}/verify_vllm_model.sh"

echo
echo "Use offline serve with snapshot path printed above, or:"
echo "  unset HF_HUB_OFFLINE   # optional if cache is complete"
echo "  export VLLM_MODEL=${MODEL}"
echo "  bash scripts/start_vllm_server.sh"
