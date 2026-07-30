#!/usr/bin/env bash
# 检查 VLLM_MODEL 或 HuggingFace 缓存目录是否包含可加载的权重文件
set -euo pipefail

MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

resolve_dir() {
  local m="$1"
  if [[ -d "$m" ]]; then
    echo "$m"
    return 0
  fi
  # HuggingFace hub layout: models--Org--Name/snapshots/<rev>
  local slug
  slug="models--${m//\//--}"
  local hub="${HF_HOME:-$HOME/.cache/huggingface}/hub/${slug}/snapshots"
  if [[ -d "$hub" ]]; then
    local snap
    snap="$(find "$hub" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)"
    if [[ -n "$snap" ]]; then
      echo "$snap"
      return 0
    fi
  fi
  return 1
}

DIR=""
if ! DIR="$(resolve_dir "$MODEL")"; then
  echo "ERROR: Cannot resolve model path for: ${MODEL}"
  echo "Set VLLM_MODEL to a local snapshot directory or a HuggingFace model ID."
  exit 1
fi

echo "Model directory: ${DIR}"
shopt -s nullglob
weights=( "${DIR}"/*.safetensors "${DIR}"/model*.bin "${DIR}"/pytorch_model*.bin )
shopt -u nullglob

if [[ ${#weights[@]} -eq 0 ]]; then
  echo "ERROR: No .safetensors or .bin weight files in ${DIR}"
  echo "Listing directory:"
  ls -la "${DIR}" || true
  echo
  echo "Fix: complete the download (requires network, do NOT set HF_HUB_OFFLINE=1):"
  echo "  cd backend && source .venv-vllm/bin/activate"
  echo "  export HF_ENDPOINT=https://hf-mirror.com"
  echo "  unset HF_HUB_OFFLINE"
  echo "  bash scripts/download_vllm_model.sh"
  exit 1
fi

echo "OK: found ${#weights[@]} weight file(s):"
for w in "${weights[@]}"; do
  if [[ -L "$w" ]]; then
    target="$(readlink -f "$w" 2>/dev/null || readlink "$w")"
    if [[ ! -f "$target" ]]; then
      echo "ERROR: broken symlink: $w -> $target"
      exit 1
    fi
    size="$(stat -c%s "$target" 2>/dev/null || stat -f%z "$target")"
    echo "  $(basename "$w") -> $(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size} bytes")"
  else
    echo "  $(basename "$w")"
  fi
done

if [[ -f "${DIR}/config.json" ]] || [[ -L "${DIR}/config.json" ]]; then
  echo "OK: config.json present"
else
  echo "WARN: config.json missing"
fi
