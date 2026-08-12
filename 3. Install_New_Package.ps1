param(
    [Parameter(Mandatory=$true)]
    [string]$Package
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$activateScript = Join-Path $root "venv\Scripts\Activate.ps1"
$requirementsFile = Join-Path $root "requirements.txt"

Write-Host "Activating venv..." -ForegroundColor Cyan
. $activateScript

Write-Host "Installing '$Package'..." -ForegroundColor Cyan
pip install $Package

Write-Host "Re-freezing requirements.txt so it always stays current..." -ForegroundColor Cyan
pip freeze > $requirementsFile

Write-Host "Done. '$Package' installed and requirements.txt updated." -ForegroundColor Green
Write-Host "Tip: run '4. Push_To_GitHub.ps1' to save this change." -ForegroundColor DarkCyan
