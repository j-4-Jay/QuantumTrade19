$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$appState = Join-Path $projectRoot 'state\app_state.py'

if (-not (Test-Path $appState)) {
    throw "Cannot find: $appState"
}

$content = [System.IO.File]::ReadAllText($appState)
$old = 'return [AppState.poll_ws_status, AppState.poll_pinned_prices]'
$new = 'return None'

if ($content.Contains($new) -and -not $content.Contains($old)) {
    Write-Host 'Fix is already installed. Nothing was changed.' -ForegroundColor Yellow
    exit 0
}

if (-not $content.Contains($old)) {
    throw "The expected AppState line was not found. No files were changed."
}

$backup = "$appState.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $appState $backup

$content = $content.Replace($old, $new)
[System.IO.File]::WriteAllText($appState, $content, [System.Text.UTF8Encoding]::new($false))

Write-Host 'Success: disconnected-client background polling has been disabled.' -ForegroundColor Green
Write-Host "Backup created: $backup" -ForegroundColor DarkGray
Write-Host 'Now stop the app, then start it again with 1. Start_QuantumTrade19.ps1.' -ForegroundColor Cyan
