param(
    [string]$Message = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  QuantumTrade19 - Push To GitHub" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $root ".git"))) {
    Write-Host "This folder is not a git repository yet." -ForegroundColor Red
    Write-Host "Run: git init, then git remote add origin <your-repo-url>, before using this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "Staging all changes..." -ForegroundColor Green
git add -A

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to commit -- working tree is already clean." -ForegroundColor DarkYellow
} else {
    Write-Host "Committing with message: `"$Message`"" -ForegroundColor Green
    git commit -m "$Message"
}

Write-Host "Pushing to origin..." -ForegroundColor Green
$currentBranch = git rev-parse --abbrev-ref HEAD

$hasUpstream = git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
if (-not $hasUpstream) {
    Write-Host "No upstream branch set yet -- setting it now (first push to '$currentBranch')..." -ForegroundColor Yellow
    git push --set-upstream origin $currentBranch
} else {
    git push
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done. Changes pushed to GitHub successfully." -ForegroundColor Green
} else {
    Write-Host "PUSH FAILED. Nothing was actually sent to GitHub -- scroll up to see the git error above." -ForegroundColor Red
    exit 1
}
