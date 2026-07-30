#!/usr/bin/env bash
# Task 2.6: run latency + throughput benchmarks and refresh docs/performance.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_ROOT}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
BASE_URL="${VLLM_BENCH_URL:-http://${IP:-127.0.0.1}:8000/v1}"

echo "vLLM base URL: ${BASE_URL}"

python -m benchmark.latency_test --backend vllm --base-url "${BASE_URL}" "$@" || true
python -m benchmark.throughput_test --backend vllm --base-url "${BASE_URL}" "$@" || true

if python -c "import torch" 2>/dev/null; then
  python -m benchmark.latency_test --backend transformers "$@" || true
  python -m benchmark.throughput_test --backend transformers "$@" || true
else
  echo "Skip Transformers benchmarks (install torch / requirements-llm in this venv)."
fi

python -m benchmark.generate_report
echo "Report: ${BACKEND_ROOT}/../docs/performance.md"
