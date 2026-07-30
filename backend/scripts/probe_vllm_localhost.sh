#!/usr/bin/env bash
# 诊断 WSL 下 vLLM localhost 连通性（mirrored 网络模式常见问题）
set -euo pipefail
PORT="${VLLM_PORT:-8000}"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo "=== ss :${PORT} ==="
ss -tlnp 2>/dev/null | grep ":${PORT}" || echo "(no listener)"

try() {
  local url="$1"
  printf '%-42s ' "$url"
  if code=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null); then
    echo "HTTP $code"
  else
    echo "FAILED ($?)"
  fi
}

echo
echo "=== curl probes ==="
try "http://127.0.0.1:${PORT}/health"
try "http://localhost:${PORT}/health"
if [[ -n "${IP}" ]]; then
  try "http://${IP}:${PORT}/health"
fi

if ss -tlnp 2>/dev/null | grep -q ":${PORT}.*127.0.0.1"; then
  :
elif ss -tlnp 2>/dev/null | grep -q ":${PORT}" && [[ -n "${IP}" ]]; then
  echo
  echo "Tip: 127.0.0.1 failed but ${IP} works → WSL mirrored/firewall loopback issue."
  echo "  curl http://${IP}:${PORT}/v1/models"
  echo "  See docs/vllm_deployment.md Q3d"
fi
