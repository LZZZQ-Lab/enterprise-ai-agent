# Task 9.4 — 运行全部 Mock Demo
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Demos = @(
    "demo_01_chat.py",
    "demo_02_rag.py",
    "demo_03_agent.py",
    "demo_04_workflow.py",
    "demo_05_software_team.py",
    "demo_06_infra.py"
)

Write-Host "==> Enterprise AI Platform — run all Mock demos"
Write-Host "    ROOT=$Root"
Write-Host ""

foreach ($demo in $Demos) {
    Write-Host "========================================"
    Write-Host ">>> python examples/$demo"
    Write-Host "========================================"
    python "examples/$demo"
    Write-Host ""
}

Write-Host "All $($Demos.Count) demos completed."
