#!/usr/bin/env bash
set -euo pipefail

echo "=== Chat from host ==="
curl -sS http://127.0.0.1:8001/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"docker-test","message":"hi"}' | head -c 600
echo

echo "=== vLLM from container: 192.168.100.102 ==="
docker exec enterprise-ai-backend-api-only curl -sS --connect-timeout 5 \
  http://192.168.100.102:8000/v1/models 2>&1 | head -c 300 || true
echo

echo "=== vLLM from container: host.docker.internal ==="
docker exec enterprise-ai-backend-api-only curl -sS --connect-timeout 5 \
  http://host.docker.internal:8000/v1/models 2>&1 | head -c 300 || true
echo

echo "=== vLLM from container: 172.17.0.1 ==="
docker exec enterprise-ai-backend-api-only curl -sS --connect-timeout 5 \
  http://172.17.0.1:8000/v1/models 2>&1 | head -c 300 || true
echo
