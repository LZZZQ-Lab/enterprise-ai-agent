#!/usr/bin/env bash
# Task 2.4: 启动 vLLM OpenAI Compatible API Server
#
# 用法:
#   cd backend
#   bash scripts/start_vllm_server.sh
#
# 环境变量:
#   VLLM_MODEL       默认 Qwen/Qwen2.5-0.5B-Instruct
#   VLLM_HOST        默认 0.0.0.0
#   VLLM_PORT        默认 8000
#   VLLM_MAX_LEN     默认 512（4GB 显存友好）
#   VLLM_GPU_UTIL    默认 0.70
#   VLLM_PROFILE     baseline | optimized（Task 4.4，见 data/vllm_profiles.json）
#   VLLM_MAX_NUM_SEQS / VLLM_MAX_BATCHED_TOKENS / VLLM_PREFIX_CACHING / VLLM_ENFORCE_EAGER
#   VLLM_SERVED_MODEL_NAME  API 上的 model id，默认 Qwen/Qwen2.5-0.5B-Instruct（与 Platform MODEL_NAME 对齐）
#   VLLM_USE_FLASHINFER_SAMPLER  未装 CUDA Toolkit(nvcc) 时脚本自动设为 0
#   VLLM_ENABLE_TOOL_CALLING  设为 1 时追加 --enable-auto-tool-choice --tool-call-parser（默认 qwen）
#   VLLM_TOOL_CALL_PARSER  默认 qwen（Qwen2.5-Instruct）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${BACKEND_ROOT}/.venv-vllm/bin/activate" ]]; then

    # shellcheck disable=SC1091
    source "${BACKEND_ROOT}/.venv-vllm/bin/activate"
    echo "Using venv: ${BACKEND_ROOT}/.venv-vllm"
    echo

fi

MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
PROFILE="${VLLM_PROFILE:-baseline}"

apply_profile_from_python() {
  local profile_name="$1"
  if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    return 1
  fi
  local py="python3"
  command -v python3 >/dev/null 2>&1 || py="python"
  "${py}" - <<'PY' "${profile_name}" "${BACKEND_ROOT}"
import json
import sys
from pathlib import Path

backend = Path(sys.argv[2])
path = backend / "data" / "vllm_profiles.json"
name = sys.argv[1]
if not path.is_file():
    sys.exit(1)
raw = json.loads(path.read_text(encoding="utf-8"))
if name not in raw:
    sys.exit(2)
item = raw[name]
print(f"export VLLM_MAX_LEN={item['max_model_len']}")
print(f"export VLLM_GPU_UTIL={item['gpu_memory_utilization']}")
print(f"export VLLM_MAX_NUM_SEQS={item['max_num_seqs']}")
print(f"export VLLM_MAX_BATCHED_TOKENS={item['max_num_batched_tokens']}")
print(f"export VLLM_SWAP_SPACE={item['swap_space_gb']}")
print(f"export VLLM_PREFIX_CACHING={1 if item.get('enable_prefix_caching') else 0}")
print(f"export VLLM_ENFORCE_EAGER={1 if item.get('enforce_eager', True) else 0}")
PY
}

PROFILE_EXPORTS=""
if PROFILE_EXPORTS="$(apply_profile_from_python "${PROFILE}" 2>/dev/null)"; then
  # shellcheck disable=SC1090
  eval "${PROFILE_EXPORTS}"
fi

MAX_LEN="${VLLM_MAX_LEN:-512}"
GPU_UTIL="${VLLM_GPU_UTIL:-0.70}"
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-16}"
MAX_BATCHED_TOKENS="${VLLM_MAX_BATCHED_TOKENS:-2048}"
SWAP_SPACE="${VLLM_SWAP_SPACE:-2}"
PREFIX_CACHING="${VLLM_PREFIX_CACHING:-0}"
ENFORCE_EAGER="${VLLM_ENFORCE_EAGER:-1}"
SERVED_MODEL_NAME="${VLLM_SERVED_MODEL_NAME:-Qwen/Qwen2.5-0.5B-Instruct}"
ENABLE_TOOL_CALLING="${VLLM_ENABLE_TOOL_CALLING:-0}"
TOOL_CALL_PARSER="${VLLM_TOOL_CALL_PARSER:-qwen}"

echo "Starting vLLM OpenAI API Server"
echo "  Model : ${MODEL}"
echo "  Served: ${SERVED_MODEL_NAME}  (use this as MODEL_NAME / curl model field)"
echo "  Profile: ${PROFILE}  max_seqs: ${MAX_NUM_SEQS}  batched_tokens: ${MAX_BATCHED_TOKENS}"
echo "  MaxLen: ${MAX_LEN}  GPU util: ${GPU_UTIL}  prefix_cache: ${PREFIX_CACHING}"
echo "  Listen: http://${HOST}:${PORT}"
echo "  Docs  : http://127.0.0.1:${PORT}/docs"
echo "  Tools : ${ENABLE_TOOL_CALLING} (parser: ${TOOL_CALL_PARSER})"
echo

export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export PYTHONUNBUFFERED=1

# HuggingFace 镜像（WSL 无法直连 huggingface.co 时使用）
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# FlashInfer 采样首次运行会 JIT 编译，需要 nvcc；WSL 常仅有驱动、无 CUDA Toolkit
if [[ -z "${VLLM_USE_FLASHINFER_SAMPLER:-}" ]] && ! command -v nvcc >/dev/null 2>&1; then
  export VLLM_USE_FLASHINFER_SAMPLER=0
  echo "Note: nvcc not found → VLLM_USE_FLASHINFER_SAMPLER=0 (PyTorch top-k/top-p sampler)"
  echo
fi

if [[ -d "${MODEL}" ]]; then
  if ! bash "${SCRIPT_DIR}/verify_vllm_model.sh"; then
    exit 1
  fi
  echo
fi

VLLM_EXTRA_ARGS=(
  --max-num-seqs "${MAX_NUM_SEQS}"
  --max-num-batched-tokens "${MAX_BATCHED_TOKENS}"
  --swap-space "${SWAP_SPACE}"
)

if [[ "${PREFIX_CACHING}" == "1" ]]; then
  VLLM_EXTRA_ARGS+=(--enable-prefix-caching)
fi

if [[ "${ENFORCE_EAGER}" == "1" ]]; then
  VLLM_EXTRA_ARGS+=(--enforce-eager)
fi

if [[ "${ENABLE_TOOL_CALLING}" == "1" ]]; then
  VLLM_EXTRA_ARGS+=(
    --enable-auto-tool-choice
    --tool-call-parser "${TOOL_CALL_PARSER}"
  )
fi

exec vllm serve "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  --max-model-len "${MAX_LEN}" \
  --gpu-memory-utilization "${GPU_UTIL}" \
  "${VLLM_EXTRA_ARGS[@]}" \
  --dtype auto \
  --trust-remote-code
