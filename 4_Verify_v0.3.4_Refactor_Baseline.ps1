$ErrorActionPreference = 'Stop'

$ProjectRoot = 'E:\QuantumTrade19'
$RequiredFiles = @(
    'state\app_state.py',
    'state\app_state_parts\01_core_shell.py',
    'state\app_state_parts\02_auth_security.py',
    'state\app_state_parts\03_market_dashboard.py',
    'state\app_state_parts\04_poi_settings.py',
    'state\app_state_parts\05_trading_panel.py',
    'state\backups\app_state_before_split_20260824_172335.py',
    'ui\components\kline_chart.py',
    'ui\components\trading_panel_chart.py',
    'ui\pages\trading_panel.py'
)

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Project root was not found: $ProjectRoot"
}

Set-Location -LiteralPath $ProjectRoot

$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OutputDir = Join-Path $ProjectRoot "tracker_files\v0.3.4_baseline_$Stamp"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Missing = @()
foreach ($RelativePath in $RequiredFiles) {
    $SourcePath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $SourcePath)) {
        $Missing += $RelativePath
        continue
    }

    $DestinationPath = Join-Path $OutputDir $RelativePath
    $DestinationFolder = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Force -Path $DestinationFolder | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
}

$PythonCheck = & python -m py_compile state\app_state.py 2>&1
$PythonExitCode = $LASTEXITCODE

$ReportPath = Join-Path $OutputDir 'baseline_report.txt'
$ReportLines = @(
    'QuantumTrade19 v0.3.4 baseline verification',
    "Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
    "Project root: $ProjectRoot",
    '',
    'Required files:',
    $RequiredFiles,
    '',
    'Missing files:',
    $(if ($Missing.Count -eq 0) { 'None' } else { $Missing }),
    '',
    "python -m py_compile state\app_state.py exit code: $PythonExitCode",
    '',
    'Compiler output:',
    $PythonCheck
)
$ReportLines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ''
Write-Host 'Baseline folder created:' -ForegroundColor Green
Write-Host $OutputDir -ForegroundColor Cyan
Write-Host ''
Write-Host 'Report created:' -ForegroundColor Green
Write-Host $ReportPath -ForegroundColor Cyan
Write-Host ''

if ($Missing.Count -gt 0) {
    Write-Host 'STOP: One or more required files are missing. Do not refactor.' -ForegroundColor Red
    exit 1
}

if ($PythonExitCode -ne 0) {
    Write-Host 'STOP: app_state.py does not compile. Do not refactor.' -ForegroundColor Red
    exit $PythonExitCode
}

Write-Host 'Baseline check passed. Do not edit .web.' -ForegroundColor Green
