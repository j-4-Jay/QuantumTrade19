<#
.SYNOPSIS
    QuantumTrade19 - Path/File Upload Bundle Creator (v1.0)

.DESCRIPTION
    Asks the user for one or more file paths, reads the full text content of
    each file, and writes them all into a single versioned .txt bundle file
    with clear BEGIN FILE / END FILE headers and separators, ready to upload
    into a new AI thread.

    TARGET PATH: D:\QuantumTrade19\7_Create_PathFile_Upload_Bundle.ps1

.NOTES
    - Read-only. Never modifies, deletes, or overwrites any source file.
    - Output bundle is saved under:
      D:\QuantumTrade19\tracker_files\thread_upload_bundles\
    - Output file name is auto-versioned (v1, v2, v3, ...) so previous
      bundles are never overwritten.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot  = "D:\QuantumTrade19"
$OutputFolder = Join-Path $ProjectRoot "tracker_files\thread_upload_bundles"

if (-not (Test-Path $OutputFolder)) {
    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
}

Write-Host "==============================================="
Write-Host " QuantumTrade19 - Path/File Upload Bundle Creator"
Write-Host "==============================================="
Write-Host ""
Write-Host "Enter one file path at a time."
Write-Host "Press ENTER on an empty line when you are done adding paths."
Write-Host ""

$paths = New-Object System.Collections.Generic.List[string]

while ($true) {
    $input = Read-Host "Enter file path (or press ENTER to finish)"
    if ([string]::IsNullOrWhiteSpace($input)) {
        break
    }
    $trimmed = $input.Trim('"').Trim()
    $paths.Add($trimmed)
}

if ($paths.Count -eq 0) {
    Write-Host ""
    Write-Host "No paths were entered. Nothing to do. Exiting."
    exit 0
}

# Determine next version number by scanning existing bundle files
$existing = Get-ChildItem -Path $OutputFolder -Filter "ThreadUploadBundle_v*.txt" -ErrorAction SilentlyContinue
$maxVersion = 0
foreach ($file in $existing) {
    if ($file.Name -match "ThreadUploadBundle_v(\d+)\.txt") {
        $found = [int]$Matches[1]
        if ($found -gt $maxVersion) { $maxVersion = $found }
    }
}
$nextVersion = $maxVersion + 1
$timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile  = Join-Path $OutputFolder ("ThreadUploadBundle_v{0}_{1}.txt" -f $nextVersion, $timestamp)

$separator = ("-" * 100)
$sb = New-Object System.Text.StringBuilder

[void]$sb.AppendLine($separator)
[void]$sb.AppendLine("QUANTUMTRADE19 - THREAD UPLOAD BUNDLE (v$nextVersion)")
[void]$sb.AppendLine("Created: $timestamp")
[void]$sb.AppendLine("Project root: $ProjectRoot")
[void]$sb.AppendLine("Total files requested: $($paths.Count)")
[void]$sb.AppendLine($separator)
[void]$sb.AppendLine("")

$successCount = 0
$failCount    = 0

foreach ($p in $paths) {

    [void]$sb.AppendLine($separator)

    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        Write-Host "NOT FOUND: $p" -ForegroundColor Red
        [void]$sb.AppendLine("FILE: $p")
        [void]$sb.AppendLine("STATUS: NOT FOUND - SKIPPED")
        [void]$sb.AppendLine($separator)
        [void]$sb.AppendLine("")
        $failCount++
        continue
    }

    try {
        $content = Get-Content -LiteralPath $p -Raw -Encoding UTF8
    }
    catch {
        Write-Host "ERROR READING: $p -> $($_.Exception.Message)" -ForegroundColor Red
        [void]$sb.AppendLine("FILE: $p")
        [void]$sb.AppendLine("STATUS: ERROR READING FILE - $($_.Exception.Message)")
        [void]$sb.AppendLine($separator)
        [void]$sb.AppendLine("")
        $failCount++
        continue
    }

    $fileName = Split-Path -Path $p -Leaf

    [void]$sb.AppendLine("BEGIN FILE: $fileName")
    [void]$sb.AppendLine("FULL PATH: $p")
    [void]$sb.AppendLine($separator)
    [void]$sb.AppendLine($content)
    [void]$sb.AppendLine($separator)
    [void]$sb.AppendLine("END FILE: $fileName")
    [void]$sb.AppendLine($separator)
    [void]$sb.AppendLine("")

    Write-Host "Added: $p" -ForegroundColor Green
    $successCount++
}

[void]$sb.AppendLine($separator)
[void]$sb.AppendLine("BUNDLE SUMMARY")
[void]$sb.AppendLine("Files successfully added: $successCount")
[void]$sb.AppendLine("Files skipped/failed: $failCount")
[void]$sb.AppendLine($separator)

Set-Content -LiteralPath $outputFile -Value $sb.ToString() -Encoding UTF8

Write-Host ""
Write-Host "==============================================="
Write-Host " DONE"
Write-Host "==============================================="
Write-Host "Bundle file created at:"
Write-Host "$outputFile"
Write-Host ""
Write-Host "Files added: $successCount   Failed/skipped: $failCount"
Write-Host ""
