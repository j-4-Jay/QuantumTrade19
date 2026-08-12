$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPath = Join-Path $root "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
$flagFile = Join-Path $venvPath "installed.flag"
$requirementsFile = Join-Path $root "requirements.txt"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  QuantumTrade19 - Starting Application" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (-not (Test-Path $venvPath)) {
    Write-Host "No venv found. Creating one now..." -ForegroundColor Yellow
    python -m venv $venvPath
}

Write-Host "Activating virtual environment..." -ForegroundColor Green
. $activateScript

$needsInstall = $false
if (-not (Test-Path $flagFile)) {
    $needsInstall = $true
} elseif ((Get-Item $requirementsFile).LastWriteTime -gt (Get-Item $flagFile).LastWriteTime) {
    $needsInstall = $true
}

if ($needsInstall) {
    Write-Host "requirements.txt changed (or first run) -- installing dependencies..." -ForegroundColor Yellow
    pip install -r $requirementsFile
    New-Item -ItemType File -Path $flagFile -Force | Out-Null
    Write-Host "Dependencies installed and flag updated." -ForegroundColor Green
} else {
    Write-Host "Dependencies already up to date." -ForegroundColor Green
}

Write-Host "Launching QuantumTrade19 (reflex run)..." -ForegroundColor Cyan
Set-Location $root
reflex run
