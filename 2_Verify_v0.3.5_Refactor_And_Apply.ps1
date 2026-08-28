$ErrorActionPreference = 'Stop'

$ProjectRoot = 'E:\QuantumTrade19'
$SourceFolder = Join-Path $ProjectRoot 'state\app_state_mixins'
$BackupFolder = Join-Path $ProjectRoot 'state\backups'
$TrackerFolder = Join-Path $ProjectRoot 'tracker_files'

$RequiredMixinFiles = @(
    'shared.py',
    'core_shell_mixin.py',
    'auth_security_mixin.py',
    'market_dashboard_mixin.py',
    'poi_settings_mixin.py',
    'trading_panel_mixin.py'
)

$RequiredUIFiles = @(
    'ui\components\kline_chart.py',
    'ui\components\trading_panel_chart.py',
    'ui\pages\trading_panel.py'
)

$AllFilesToCompile = @(
    'state\app_state_mixins\shared.py',
    'state\app_state_mixins\core_shell_mixin.py',
    'state\app_state_mixins\auth_security_mixin.py',
    'state\app_state_mixins\market_dashboard_mixin.py',
    'state\app_state_mixins\poi_settings_mixin.py',
    'state\app_state_mixins\trading_panel_mixin.py',
    'state\app_state.py'
) + $RequiredUIFiles

# Verify all source files exist
$Missing = @()
foreach ($File in $RequiredMixinFiles) {
    $Path = Join-Path $SourceFolder $File
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $Missing += "state\app_state_mixins\$File"
    }
}
foreach ($File in $RequiredUIFiles) {
    $Path = Join-Path $ProjectRoot $File
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $Missing += $File
    }
}
if ($Missing.Count -gt 0) {
    throw "Missing required source files:`n$($Missing -join "`n")"
}

# Create backup of current app_state.py
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$BackupPath = Join-Path $BackupFolder "app_state_before_v0.3.5_mixin_refactor_$Stamp.py"
New-Item -ItemType Directory -Force -Path $BackupFolder | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'state\app_state.py') -Destination $BackupPath -Force

# Compile all files first
Write-Host "Compiling all files..." -ForegroundColor Cyan
foreach ($RelativePath in $AllFilesToCompile) {
    $FullPath = Join-Path $ProjectRoot $RelativePath
    & python -m py_compile $FullPath
    if ($LASTEXITCODE -ne 0) {
        throw "Compile failed for $RelativePath. No changes applied."
    }
}

# All compiles passed - apply the new files (they are already in place from download)
Write-Host "All files compile successfully." -ForegroundColor Green

# Final verification compile of app_state.py
& python -m py_compile (Join-Path $ProjectRoot 'state\app_state.py')
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath $BackupPath -Destination (Join-Path $ProjectRoot 'state\app_state.py') -Force
    throw "Final app_state.py compile failed. Restored from backup."
}

Write-Host ""
Write-Host "SUCCESS - v0.3.5 executable mixin refactor applied." -ForegroundColor Green
Write-Host "Backup: $BackupPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT: Start the app and verify runtime behavior." -ForegroundColor Yellow
Write-Host "Then proceed to Trading Panel OHLC-only polling fix." -ForegroundColor Yellow
