# FULL PATH: E:\QuantumTrade19\1. Start_QuantumTrade19.ps1
# REPLACE THE ENTIRE EXISTING FILE WITH THIS FILE.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPath = Join-Path $root "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
$flagFile = Join-Path $venvPath "installed.flag"
$requirementsFile = Join-Path $root "requirements.txt"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  QuantumTrade19 - Starting Application" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $venvPath)) {
    Write-Host "No venv found. Creating one now..." -ForegroundColor Yellow
    python -m venv $venvPath
}

if (-not (Test-Path -LiteralPath $activateScript)) {
    throw "Virtual-environment activation file was not created: $activateScript"
}

Write-Host "Activating virtual environment..." -ForegroundColor Green
. $activateScript

$needsInstall = -not (Test-Path -LiteralPath $flagFile)
if (-not $needsInstall -and (Test-Path -LiteralPath $requirementsFile)) {
    $needsInstall = (Get-Item -LiteralPath $requirementsFile).LastWriteTime -gt (Get-Item -LiteralPath $flagFile).LastWriteTime
}

if ($needsInstall) {
    Write-Host "requirements.txt changed (or first run) -- installing dependencies..." -ForegroundColor Yellow
    python -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
    New-Item -ItemType File -Path $flagFile -Force | Out-Null
    Write-Host "Dependencies installed and flag updated." -ForegroundColor Green
} else {
    Write-Host "Dependencies already up to date." -ForegroundColor Green
}

Write-Host "Launching QuantumTrade19..." -ForegroundColor Cyan
Set-Location $root

# Reflex emits these known development-only messages directly to the terminal.
# Filter only those messages; all other startup output and all real errors remain visible.
$insideRadixWarning = $false
$skipDisconnectedClientId = $false

& reflex run 2>&1 | ForEach-Object {
    $line = $_.ToString()

    if ($skipDisconnectedClientId) {
        $skipDisconnectedClientId = $false
        if ($line -match '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}') {
            return
        }
    }

    if ($line -match 'Windows Subsystem for Linux \(WSL\) is recommended') {
        return
    }

    if ($line -match 'DeprecationWarning: Implicit Radix Themes enablement') {
        $insideRadixWarning = $true
        return
    }

    if ($insideRadixWarning) {
        if ($line -match 'reflex_components_radix[\\/]plugin\.py:\d+\)') {
            $insideRadixWarning = $false
        }
        return
    }

    if ($line -match 'Warning: Attempting to send delta to disconnected client') {
        $skipDisconnectedClientId = $true
        return
    }

    Write-Host $line
}

exit $LASTEXITCODE
