$ErrorActionPreference = 'Stop'

$DownloadsFolder = $PSScriptRoot
$Today = (Get-Date).Date

Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '  QuantumTrade19 - Replace From Downloads' -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Paste the "What to do now" file paths below (one per line).' -ForegroundColor Yellow
Write-Host 'When you are finished pasting, press Enter on an EMPTY line, then Enter again.' -ForegroundColor Yellow
Write-Host ''

$RawLines = New-Object 'System.Collections.Generic.List[string]'
$EmptyStreak = 0
while ($true) {
    $Line = Read-Host
    if ([string]::IsNullOrWhiteSpace($Line)) {
        $EmptyStreak++
        if ($EmptyStreak -ge 1 -and $RawLines.Count -gt 0) {
            break
        }
        continue
    }
    $EmptyStreak = 0
    $RawLines.Add($Line)
}

function Get-CleanPath {
    param([string]$Line)
    $Value = $Line.Trim().Trim('`', '"', "'", ' ')
    if ($Value -match '^(?:BEGIN FILE:|FULL PATH:|END FILE:)\s*(.+)$') {
        $Value = $Matches[1].Trim().Trim('`', '"', "'", ' ')
    }
    if ($Value -match '^[A-Za-z]:\\.+\.[A-Za-z0-9]{1,10}$') {
        return $Value
    }
    return $null
}

$TargetPaths = New-Object 'System.Collections.Generic.List[string]'
$Seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($Line in $RawLines) {
    $Cleaned = Get-CleanPath -Line $Line
    if ($Cleaned -and $Seen.Add($Cleaned)) {
        [void]$TargetPaths.Add($Cleaned)
    }
}

if ($TargetPaths.Count -eq 0) {
    Write-Host ''
    Write-Host 'No valid file paths were detected in the pasted text. Nothing to do.' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host "Detected $($TargetPaths.Count) target file path(s)." -ForegroundColor Green
Write-Host ''

$Results = New-Object 'System.Collections.Generic.List[pscustomobject]'

foreach ($TargetPath in $TargetPaths) {
    $FileName = Split-Path -Leaf $TargetPath
    $BaseName = [System.IO.Path]::GetFileNameWithoutExtension($FileName)
    $Extension = [System.IO.Path]::GetExtension($FileName)

    $ExactMatches = Get-ChildItem -LiteralPath $DownloadsFolder -File -Filter $FileName -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime.Date -eq $Today }

    $SourceFile = $null
    if ($ExactMatches) {
        $SourceFile = $ExactMatches | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    else {
        $FuzzyPattern = "$BaseName*$Extension"
        $FuzzyMatches = Get-ChildItem -LiteralPath $DownloadsFolder -File -Filter $FuzzyPattern -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime.Date -eq $Today }
        if ($FuzzyMatches) {
            $SourceFile = $FuzzyMatches | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        }
    }

    if (-not $SourceFile) {
        $Results.Add([pscustomobject]@{
            TargetPath = $TargetPath
            FileName   = $FileName
            SourceFile = ''
            Status     = 'NOT FOUND in downloads (today)'
        })
        continue
    }

    try {
        $TargetFolder = Split-Path -Parent $TargetPath
        if (-not (Test-Path -LiteralPath $TargetFolder)) {
            New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
        }

        if (Test-Path -LiteralPath $TargetPath) {
            $Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $BackupPath = "$TargetPath.bak_$Stamp"
            Copy-Item -LiteralPath $TargetPath -Destination $BackupPath -Force
        }

        Copy-Item -LiteralPath $SourceFile.FullName -Destination $TargetPath -Force

        $Results.Add([pscustomobject]@{
            TargetPath = $TargetPath
            FileName   = $FileName
            SourceFile = $SourceFile.FullName
            Status     = 'REPLACED'
        })
    }
    catch {
        $Results.Add([pscustomobject]@{
            TargetPath = $TargetPath
            FileName   = $FileName
            SourceFile = $SourceFile.FullName
            Status     = "FAILED: $($_.Exception.Message)"
        })
    }
}

Write-Host ''
Write-Host '--------------------------------------------' -ForegroundColor Cyan
Write-Host '  REPLACEMENT REPORT' -ForegroundColor Cyan
Write-Host '--------------------------------------------' -ForegroundColor Cyan
foreach ($Result in $Results) {
    $Color = switch -Wildcard ($Result.Status) {
        'REPLACED' { 'Green' }
        'NOT FOUND*' { 'Yellow' }
        default { 'Red' }
    }
    Write-Host "$($Result.Status)" -ForegroundColor $Color -NoNewline
    Write-Host "  ->  $($Result.TargetPath)"
}

$ReplacedCount = ($Results | Where-Object { $_.Status -eq 'REPLACED' }).Count
$NotFoundCount = ($Results | Where-Object { $_.Status -like 'NOT FOUND*' }).Count
$FailedCount = ($Results | Where-Object { $_.Status -like 'FAILED*' }).Count

Write-Host ''
Write-Host "Replaced: $ReplacedCount   Not found: $NotFoundCount   Failed: $FailedCount" -ForegroundColor Cyan

$ReportStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$ReportPath = Join-Path $DownloadsFolder "Replace_Report_$ReportStamp.txt"

$ReportLines = New-Object 'System.Collections.Generic.List[string]'
$ReportLines.Add('QuantumTrade19 - Replace From Downloads Report')
$ReportLines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')")
$ReportLines.Add("Downloads folder scanned: $DownloadsFolder")
$ReportLines.Add('')
foreach ($Result in $Results) {
    $ReportLines.Add("Status:     $($Result.Status)")
    $ReportLines.Add("Target:     $($Result.TargetPath)")
    $ReportLines.Add("Source:     $($Result.SourceFile)")
    $ReportLines.Add('')
}
$ReportLines.Add("Replaced: $ReplacedCount   Not found: $NotFoundCount   Failed: $FailedCount")

$ReportLines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ''
Write-Host 'Report saved to:' -ForegroundColor Yellow
Write-Host $ReportPath -ForegroundColor Cyan
Write-Host ''
