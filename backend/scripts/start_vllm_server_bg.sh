#!/usr/bin/env bash
# 后台启动 vLLM，日志写到 backend/logs（Windows 可读）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
mkdir -p "${BACKEND_ROOT}/logs"
LOG="${BACKEND_ROOT}/logs/vllm_server.log"

cd "${BACKEND_ROOT}"
export VLLM_MAX_LEN="${VLLM_MAX_LEN:-512}"
export VLLM_GPU_UTIL="${VLLM_GPU_UTIL:-0.70}"
export PYTHONUNBUFFERED=1

pkill -f "vllm serve" 2>/dev/null || true
sleep 2

nohup bash scripts/start_vllm_server.sh >>"${LOG}" 2>&1 &
echo "vLLM starting in background, pid=$!"
echo "Log: ${LOG}"
echo "Tail: tail -f ${LOG}"
