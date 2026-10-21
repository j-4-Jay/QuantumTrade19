# 4. Project_Operations.ps1 - launcher for the Project_Operations Python core (v2.0.1)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $here
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$py = $null
$pyArgs = @()
if (Test-Path -LiteralPath (Join-Path $here "venv\Scripts\python.exe")) { $py = Join-Path $here "venv\Scripts\python.exe" }
elseif (Test-Path -LiteralPath (Join-Path $here ".venv\Scripts\python.exe")) { $py = Join-Path $here ".venv\Scripts\python.exe" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py"; $pyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
if (-not $py) { Write-Host "Python 3 was not found." -ForegroundColor Red; exit 1 }
& $py @pyArgs (Join-Path $here "4. Project_Operations_Core.py") @args
exit $LASTEXITCODE
