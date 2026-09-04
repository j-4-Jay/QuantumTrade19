# QuantumTrade19 v0.4.8 - Read-safe historical manifest repair
# TARGET PATH: D:\QuantumTrade19\Repair_QT19_Historical_Coverage_v0.4.8.ps1
# This script never changes candle rows. It backs up JSON manifests and rebuilds
# them from physically stored rows in data\historical\candles.db.

[CmdletBinding()]
param(
    [string]$ProjectRoot = "D:\QuantumTrade19"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$databasePath = Join-Path $ProjectRoot "data\historical\candles.db"
$manifestDirectory = Join-Path $ProjectRoot "data\historical\manifests"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDirectory = Join-Path $ProjectRoot "data\historical\manifest_backups\v0.4.8_$timestamp"

if (-not (Test-Path -LiteralPath $databasePath)) {
    throw "SQLite candle database was not found: $databasePath"
}

New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null

Get-ChildItem -LiteralPath $manifestDirectory -Filter "*.json" -File -ErrorAction SilentlyContinue |
    Copy-Item -Destination $backupDirectory -Force

$python = @'
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

project_root = Path(sys.argv[1])
database_path = project_root / "data" / "historical" / "candles.db"
manifest_dir = project_root / "data" / "historical" / "manifests"
manifest_dir.mkdir(parents=True, exist_ok=True)

steps = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
conn = sqlite3.connect(str(database_path))
try:
    rows = conn.execute(
        """
        SELECT symbol, timeframe, open_time
        FROM candles
        WHERE timeframe IN ('1m', '5m', '15m')
        ORDER BY symbol ASC, timeframe ASC, open_time ASC
        """
    ).fetchall()
finally:
    conn.close()

by_key = defaultdict(list)
for symbol, timeframe, open_time in rows:
    by_key[(symbol, timeframe)].append(int(open_time))

by_symbol = defaultdict(dict)
summary = []
for (symbol, timeframe), timestamps in by_key.items():
    step = steps[timeframe]
    ranges = []
    start = previous = timestamps[0]
    for current in timestamps[1:]:
        if current != previous + step:
            ranges.append([start, previous + step])
            start = current
        previous = current
    ranges.append([start, previous + step])
    by_symbol[symbol][timeframe] = ranges
    span_ms = sum(end - start for start, end in ranges)
    summary.append({
        "symbol": symbol,
        "timeframe": timeframe,
        "physical_rows": len(timestamps),
        "continuous_ranges": len(ranges),
        "covered_days": round(span_ms / 86_400_000, 3),
        "earliest_open_time_ms": timestamps[0],
        "latest_open_time_ms": timestamps[-1],
    })

for symbol, payload in by_symbol.items():
    path = manifest_dir / f"{symbol}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

summary_path = manifest_dir / "v0.4.8_manifest_repair_report.json"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"rebuilt_symbol_files": len(by_symbol), "coverage_records": summary}, indent=2))
'@

Write-Host ""
Write-Host "QT19 v0.4.8 historical manifest repair" -ForegroundColor Cyan
Write-Host "Candle database (read only): $databasePath"
Write-Host "Manifest backup directory:     $backupDirectory"
Write-Host ""

$python | python - $ProjectRoot

Write-Host ""
Write-Host "SUCCESS: Candle rows were not modified." -ForegroundColor Green
Write-Host "Rebuilt manifests: $manifestDirectory"
Write-Host "Report:            $(Join-Path $manifestDirectory 'v0.4.8_manifest_repair_report.json')"
