# Lean 백테스트 Docker 실행 스크립트 (Windows)
param(
    [string]$AlgoDir = "$PSScriptRoot/../lean-algo",
    [string]$DataDir = "$PSScriptRoot/../data",
    [string]$ResultsDir = "$PSScriptRoot/../results",
    [string]$ConfigPath = "$PSScriptRoot/../lean-algo/lean_launcher_config.json"
)

$AlgoDir = Resolve-Path $AlgoDir
$DataDir = Resolve-Path $DataDir
$ResultsDir = Resolve-Path $ResultsDir
$ConfigPath = Resolve-Path $ConfigPath

if (-not (Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir | Out-Null
}

Write-Host "Running Lean backtest..."
Write-Host "  Algorithm : $AlgoDir"
Write-Host "  Data      : $DataDir"
Write-Host "  Results   : $ResultsDir"

# Docker run (PowerShell)
docker run --rm `
  -v "${AlgoDir}:/Lean/Launcher/bin/Debug/Algorithms" `
  -v "${DataDir}:/Data" `
  -v "${ResultsDir}:/Results" `
  -e PYTHONPATH=/Lean/Launcher/bin/Debug/Algorithms `
  quantconnect/lean:latest `
  --config=/Lean/Launcher/bin/Debug/Algorithms/lean_launcher_config.json

Write-Host "Backtest finished. Results in $ResultsDir"
