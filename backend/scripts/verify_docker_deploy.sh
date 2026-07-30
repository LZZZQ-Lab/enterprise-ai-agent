#!/usr/bin/env bash
# Docker 部署后一键验证
set -euo pipefail

BASE="http://127.0.0.1:8001"
PASS=0
FAIL=0

check() {
  local name="$1"
  local ok="$2"
  if [[ "$ok" == "1" ]]; then
    echo "[PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "[FAIL] $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "========== Docker 部署验证 =========="
echo

# 1. 容器状态
if docker ps --filter name=enterprise-ai-backend --format '{{.Status}}' | grep -qi healthy; then
  check "容器 healthy" 1
else
  STATUS=$(docker ps --filter name=enterprise-ai-backend --format '{{.Status}}' 2>/dev/null || echo "not running")
  echo "[FAIL] 容器 healthy (当前: $STATUS)"
  FAIL=$((FAIL + 1))
fi

# 2. Health
if curl -fsS --connect-timeout 5 "$BASE/health" >/dev/null 2>&1; then
  check "GET /health" 1
else
  check "GET /health" 0
fi

# 3. Dashboard overview
if curl -fsS --connect-timeout 5 "$BASE/api/v1/infra/dashboard/overview" | grep -q '"models"'; then
  check "GET /api/v1/infra/dashboard/overview" 1
else
  check "GET /api/v1/infra/dashboard/overview" 0
fi

# 4. Dashboard demo HTML
if curl -fsS --connect-timeout 5 "$BASE/infra/dashboard/demo" | grep -qi 'overview'; then
  check "GET /infra/dashboard/demo" 1
else
  check "GET /infra/dashboard/demo" 0
fi

# 5. vLLM 从容器内可达性
WSL_IP=$(hostname -I | cut -d' ' -f1)
VLLM_OK=0
for URL in "http://${WSL_IP}:8000/v1/models" "http://host.docker.internal:8000/v1/models"; do
  if docker exec enterprise-ai-backend-api-only curl -fsS --connect-timeout 5 "$URL" >/dev/null 2>&1; then
    echo "[INFO] 容器可访问 vLLM: $URL"
    VLLM_OK=1
    break
  fi
done
if [[ "$VLLM_OK" == "1" ]]; then
  check "容器 → vLLM 连通" 1
else
  check "容器 → vLLM 连通（Docker 网络隔离，Chat 可能失败）" 0
fi

# 6. Chat
CHAT=$(curl -fsS --connect-timeout 120 -X POST "$BASE/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"docker-verify","message":"hi"}' 2>/dev/null || echo '{}')
if echo "$CHAT" | grep -q '"success": true'; then
  check "POST /api/v1/chat" 1
  echo "$CHAT" | head -c 400
  echo
elif echo "$CHAT" | grep -q 'Connection error'; then
  check "POST /api/v1/chat（Connection error：需 WSL uvicorn 或 mirrored 网络）" 0
else
  check "POST /api/v1/chat" 0
  echo "$CHAT" | head -c 400
  echo
fi

echo
echo "========== 结果: $PASS 通过, $FAIL 失败 =========="
echo "Swagger:    $BASE/docs"
echo "Dashboard:  $BASE/infra/dashboard/demo"
echo

exit $([[ "$FAIL" -eq 0 ]] && echo 0 || echo 1)
