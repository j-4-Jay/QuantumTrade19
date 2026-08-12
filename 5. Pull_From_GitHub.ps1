$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  QuantumTrade19 - Pull From GitHub" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $root ".git"))) {
    Write-Host "This folder is not a git repository yet." -ForegroundColor Red
    Write-Host "Run: git init, then git remote add origin <your-repo-url>, before using this script." -ForegroundColor Yellow
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Host "You have local uncommitted changes. Stashing them safely before pulling..." -ForegroundColor Yellow
    git stash push -m "auto-stash before pull"
    $stashed = $true
} else {
    $stashed = $false
}

Write-Host "Pulling latest changes from origin..." -ForegroundColor Green
git pull

if ($stashed) {
    Write-Host "Restoring your local changes on top of the pulled update..." -ForegroundColor Yellow
    git stash pop
}

Write-Host "Done. Local folder is up to date with GitHub." -ForegroundColor Cyan
Write-Host "Tip: run '3. Install_New_Package.ps1' related steps again if requirements.txt changed." -ForegroundColor DarkCyan
