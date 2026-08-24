# PATH: state\2_Merge_AppState.ps1
# Run from the QuantumTrade19 project root after replacing any returned parts:
#   .\state\2_Merge_AppState.ps1
#
# Merges the six app_state_part_XX.txt files in numeric order into app_state.py.
# Creates a timestamped backup first, validates Python syntax using the active
# Python interpreter, then replaces app_state.py only if validation succeeds.

[CmdletBinding()]
param(
    [switch]$KeepParts
)

$ErrorActionPreference = "Stop"

$scriptDirectory = Split-Path -Parent $PSCommandPath
$sourcePath = Join-Path $scriptDirectory "app_state.py"
$manifestPath = Join-Path $scriptDirectory "app_state_parts_manifest.json"
$temporaryPath = Join-Path $scriptDirectory "app_state.py.merge_tmp"
$backupDirectory = Join-Path $scriptDirectory "app_state_backups"
$partCount = 6

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Cannot find manifest: $manifestPath. Run .\state\1_Split_AppState.ps1 first."
}

$missingParts = @()
$partPaths = @()
for ($index = 1; $index -le $partCount; $index++) {
    $partName = "app_state_part_{0:D2}.txt" -f $index
    $partPath = Join-Path $scriptDirectory $partName
    if (-not (Test-Path -LiteralPath $partPath)) {
        $missingParts += $partName
    }
    $partPaths += $partPath
}

if ($missingParts.Count -gt 0) {
    throw "Missing part file(s): $($missingParts -join ', ')"
}

$mergedContent = ""
foreach ($partPath in $partPaths) {
    $mergedContent += [System.IO.File]::ReadAllText($partPath, [System.Text.UTF8Encoding]::new($false))
}

if ([string]::IsNullOrWhiteSpace($mergedContent)) {
    throw "Merged content is empty. app_state.py was not changed."
}

[System.IO.File]::WriteAllText($temporaryPath, $mergedContent, [System.Text.UTF8Encoding]::new($false))

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    throw "Python was not found on PATH. Activate the QuantumTrade19 venv, then run this script again."
}

& python -m py_compile $temporaryPath
if ($LASTEXITCODE -ne 0) {
    Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    throw "Merged app_state.py failed Python syntax validation. app_state.py was NOT changed."
}

New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupDirectory "app_state_$timestamp.py"

if (Test-Path -LiteralPath $sourcePath) {
    Copy-Item -LiteralPath $sourcePath -Destination $backupPath -Force
}

Move-Item -LiteralPath $temporaryPath -Destination $sourcePath -Force

Write-Host "Done. Rebuilt:" -ForegroundColor Green
Write-Host "  $sourcePath" -ForegroundColor Cyan
Write-Host "Backup saved:" -ForegroundColor Green
Write-Host "  $backupPath" -ForegroundColor Cyan

if (-not $KeepParts) {
    foreach ($partPath in $partPaths) {
        Remove-Item -LiteralPath $partPath -Force
    }
    Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
    Write-Host "Deleted the six temporary part files and manifest." -ForegroundColor DarkGray
}
else {
    Write-Host "Kept the six parts and manifest because -KeepParts was used." -ForegroundColor Yellow
}
