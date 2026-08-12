$ErrorActionPreference = "SilentlyContinue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  QuantumTrade19 - Stopping Application" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$frontendPort = 3000
$backendPort = 8000
$stopped = $false

foreach ($port in @($frontendPort, $backendPort)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $procId = $conn.OwningProcess
        if ($procId) {
            Write-Host "Stopping process on port $port (PID $procId)..." -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
    }
}

$reflexProcs = Get-Process | Where-Object { $_.ProcessName -match "reflex|python" -and $_.MainWindowTitle -match "QuantumTrade19" }
foreach ($p in $reflexProcs) {
    Write-Host "Stopping lingering process: $($p.ProcessName) (PID $($p.Id))" -ForegroundColor Yellow
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    $stopped = $true
}

if ($stopped) {
    Write-Host "QuantumTrade19 stopped successfully." -ForegroundColor Green
} else {
    Write-Host "No running QuantumTrade19 process was found." -ForegroundColor DarkYellow
}
