# Task 2.4: Windows 下启动 vLLM（推荐 WSL2 / Linux）
#
# 用法:
#   cd backend
#   powershell -ExecutionPolicy Bypass -File scripts/start_vllm_server.ps1
#
# 若已安装 WSL2 + Ubuntu，将自动在 WSL 中启动官方 vLLM 服务。

param(
    [string]$Model = $env:VLLM_MODEL,
    [string]$Host = $env:VLLM_HOST,
    [string]$Port = $env:VLLM_PORT
)

if (-not $Model) { $Model = "Qwen/Qwen2.5-0.5B-Instruct" }
if (-not $Host) { $Host = "0.0.0.0" }
if (-not $Port) { $Port = "8000" }

$backendRoot = Split-Path $PSScriptRoot -Parent
$bashScript = Join-Path $backendRoot "scripts/start_vllm_server.sh"

Write-Host "Task 2.4 vLLM Server Launcher"
Write-Host "Model : $Model"
Write-Host "Port  : $Port"
Write-Host

if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "Detected WSL. Starting vLLM inside WSL..."
    $linuxPath = wsl wslpath -a $backendRoot
    wsl bash -lc "cd '$linuxPath' && source .venv-vllm/bin/activate 2>/dev/null || true; VLLM_MODEL='$Model' VLLM_HOST='$Host' VLLM_PORT='$Port' bash scripts/start_vllm_server.sh"
    exit $LASTEXITCODE
}

Write-Host "WSL not found. Native Windows vLLM is not officially supported." -ForegroundColor Yellow
Write-Host "Options:"
Write-Host "  1) Install WSL2 + Ubuntu, then re-run this script"
Write-Host "  2) Deploy on Linux GPU server (see docs/vllm_deployment.md)"
Write-Host "  3) Use community Windows build (see docs/vllm_deployment.md FAQ)"
Write-Host
Write-Host "Direct Linux command:"
Write-Host "  VLLM_MAX_LEN=512 VLLM_GPU_UTIL=0.70 bash scripts/start_vllm_server.sh"
exit 1
