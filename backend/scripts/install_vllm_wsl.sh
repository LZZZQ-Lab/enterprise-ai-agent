#!/usr/bin/env bash
# WSL 下安装 vLLM（带重试，应对 download.pytorch.org 不稳定）
#
# 用法:
#   cd backend
#   bash scripts/install_vllm_wsl.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_ROOT}"

if [[ ! -f .venv-vllm/bin/activate ]]; then

    python3 -m venv .venv-vllm

fi

# shellcheck disable=SC1091
source .venv-vllm/bin/activate

pip install -U pip

MAX_ROUNDS="${VLLM_INSTALL_RETRIES:-5}"

for round in $(seq 1 "${MAX_ROUNDS}"); do

    echo "=== Install round ${round}/${MAX_ROUNDS} ==="

    if pip install \
        --default-timeout=600 \
        --retries 10 \
        torch \
        --index-url https://download.pytorch.org/whl/cu124; then

        break

    fi

    if [[ "${round}" -eq "${MAX_ROUNDS}" ]]; then

        echo "ERROR: torch install failed after ${MAX_ROUNDS} rounds."
        exit 1

    fi

    echo "Retrying torch install in 10s ..."
    sleep 10

done

for round in $(seq 1 "${MAX_ROUNDS}"); do

    echo "=== vLLM round ${round}/${MAX_ROUNDS} ==="

    if pip install \
        --default-timeout=600 \
        --retries 10 \
        -r requirements-vllm.txt; then

        python -c "import torch, vllm; print('torch', torch.__version__); print('vllm', vllm.__version__)"
        echo "Install OK."
        exit 0

    fi

    if [[ "${round}" -eq "${MAX_ROUNDS}" ]]; then

        echo "ERROR: vllm install failed after ${MAX_ROUNDS} rounds."
        exit 1

    fi

    echo "Retrying vllm install in 10s ..."
    sleep 10

done
