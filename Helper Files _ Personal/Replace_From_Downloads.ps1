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
            TargetPath  = $TargetPath
            FileName    = $FileName
            SourceFile  = ''
            WasExisting = $false
            Status      = 'NOT FOUND in downloads (today)'
        })
        continue
    }

    # FIX (report accuracy): capture whether the target ALREADY EXISTED
    # BEFORE any backup/copy happens - this is what actually distinguishes
    # a genuine REPLACE (an existing file on disk got overwritten, and a
    # .bak_<timestamp> backup was made) from a NEW FILE (nothing existed
    # at that path before - it was simply pasted into place, no backup
    # needed or made).
    $WasExisting = Test-Path -LiteralPath $TargetPath

    try {
        $TargetFolder = Split-Path -Parent $TargetPath
        if (-not (Test-Path -LiteralPath $TargetFolder)) {
            New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
        }

        if ($WasExisting) {
            $Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $BackupPath = "$TargetPath.bak_$Stamp"
            Copy-Item -LiteralPath $TargetPath -Destination $BackupPath -Force
        }

        Copy-Item -LiteralPath $SourceFile.FullName -Destination $TargetPath -Force

        $Results.Add([pscustomobject]@{
            TargetPath  = $TargetPath
            FileName    = $FileName
            SourceFile  = $SourceFile.FullName
            WasExisting = $WasExisting
            Status      = if ($WasExisting) { 'REPLACED' } else { 'NEW FILE (created)' }
        })
    }
    catch {
        $Results.Add([pscustomobject]@{
            TargetPath  = $TargetPath
            FileName    = $FileName
            SourceFile  = $SourceFile.FullName
            WasExisting = $WasExisting
            Status      = "FAILED: $($_.Exception.Message)"
        })
    }
}

# FIX: report is now split into clearly labeled sections - REPLACED FILES
# (existing files on disk that got overwritten, backup made) and NEW
# FILES (nothing existed at that path before, so it was simply pasted
# into place) - plus the existing NOT FOUND / FAILED sections, unchanged
# in style from before.
$ReplacedResults = $Results | Where-Object { $_.Status -eq 'REPLACED' }
$NewFileResults  = $Results | Where-Object { $_.Status -eq 'NEW FILE (created)' }
$NotFoundResults = $Results | Where-Object { $_.Status -like 'NOT FOUND*' }
$FailedResults   = $Results | Where-Object { $_.Status -like 'FAILED*' }

function Write-ReportSection {
    param(
        [string]$Title,
        [System.Collections.Generic.IEnumerable[object]]$Items,
        [string]$Color
    )
    if (-not $Items -or @($Items).Count -eq 0) { return }
    Write-Host ''
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host ('  ' + ('-' * $Title.Length)) -ForegroundColor $Color
    foreach ($Item in $Items) {
        Write-Host "  $($Item.FileName)" -ForegroundColor $Color -NoNewline
        Write-Host "  ->  $($Item.TargetPath)"
    }
}

Write-Host ''
Write-Host '--------------------------------------------' -ForegroundColor Cyan
Write-Host '  REPLACEMENT REPORT' -ForegroundColor Cyan
Write-Host '--------------------------------------------' -ForegroundColor Cyan

Write-ReportSection -Title 'REPLACED FILES (existing file overwritten, backup saved)' -Items $ReplacedResults -Color 'Green'
Write-ReportSection -Title 'NEW FILES (pasted into a fresh path, no prior file existed)' -Items $NewFileResults -Color 'Cyan'
Write-ReportSection -Title 'NOT FOUND (no matching download from today)' -Items $NotFoundResults -Color 'Yellow'
Write-ReportSection -Title 'FAILED' -Items $FailedResults -Color 'Red'

$ReplacedCount = @($ReplacedResults).Count
$NewFileCount  = @($NewFileResults).Count
$NotFoundCount = @($NotFoundResults).Count
$FailedCount   = @($FailedResults).Count

Write-Host ''
Write-Host "Replaced: $ReplacedCount   New files: $NewFileCount   Not found: $NotFoundCount   Failed: $FailedCount" -ForegroundColor Cyan

$ReportStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$ReportPath = Join-Path $DownloadsFolder "Replace_Report_$ReportStamp.txt"

$ReportLines = New-Object 'System.Collections.Generic.List[string]'
$ReportLines.Add('QuantumTrade19 - Replace From Downloads Report')
$ReportLines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')")
$ReportLines.Add("Downloads folder scanned: $DownloadsFolder")
$ReportLines.Add('')

function Add-ReportSectionLines {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Title,
        [System.Collections.Generic.IEnumerable[object]]$Items
    )
    if (-not $Items -or @($Items).Count -eq 0) { return }
    $Lines.Add("== $Title ==")
    foreach ($Item in $Items) {
        $Lines.Add("Status:     $($Item.Status)")
        $Lines.Add("Target:     $($Item.TargetPath)")
        $Lines.Add("Source:     $($Item.SourceFile)")
        $Lines.Add('')
    }
}

Add-ReportSectionLines -Lines $ReportLines -Title 'REPLACED FILES (existing file overwritten, backup saved)' -Items $ReplacedResults
Add-ReportSectionLines -Lines $ReportLines -Title 'NEW FILES (pasted into a fresh path, no prior file existed)' -Items $NewFileResults
Add-ReportSectionLines -Lines $ReportLines -Title 'NOT FOUND (no matching download from today)' -Items $NotFoundResults
Add-ReportSectionLines -Lines $ReportLines -Title 'FAILED' -Items $FailedResults

$ReportLines.Add("Replaced: $ReplacedCount   New files: $NewFileCount   Not found: $NotFoundCount   Failed: $FailedCount")

$ReportLines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ''
Write-Host 'Report saved to:' -ForegroundColor Yellow
Write-Host $ReportPath -ForegroundColor Cyan
Write-Host ''
