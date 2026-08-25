[CmdletBinding()]
param(
    [string]$TrackerName = ""
)

$ErrorActionPreference = "Stop"

function Test-ProjectRoot {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    return (
        (Test-Path -LiteralPath (Join-Path $Path "requirements.txt") -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path "state\app_state.py") -PathType Leaf)
    )
}

function Find-ProjectRoot {
    $starts = @($PSScriptRoot, (Get-Location).Path) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($start in $starts) {
        $node = Get-Item -LiteralPath $start -ErrorAction Stop
        if (-not $node.PSIsContainer) {
            $node = $node.Directory
        }

        while ($null -ne $node) {
            if ($seen.Add($node.FullName) -and (Test-ProjectRoot $node.FullName)) {
                return $node.FullName
            }
            $node = $node.Parent
        }
    }

    throw "QuantumTrade19 root was not found. Required root files: requirements.txt and state\app_state.py."
}

function Get-VersionKey {
    param([string]$Name)

    $match = [regex]::Match($Name, 'v(\d+)\.(\d+)\.(\d+)', 'IgnoreCase')
    if ($match.Success) {
        return [pscustomobject]@{
            Major = [int]$match.Groups[1].Value
            Minor = [int]$match.Groups[2].Value
            Patch = [int]$match.Groups[3].Value
        }
    }

    return [pscustomobject]@{
        Major = -1
        Minor = -1
        Patch = -1
    }
}

function Get-ProjectRelativePath {
    param(
        [string]$Path,
        [string]$Root
    )

    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($Root.Length).TrimStart('\', '/')
    }

    return $full
}

function Resolve-ProjectPath {
    param(
        [string]$RawPath,
        [string]$Root,
        [string]$ProjectLeaf
    )

    $value = $RawPath.Trim().Trim('`', ' ', '"', "'") -replace '/', '\'
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $null
    }

    if (-not [System.IO.Path]::IsPathRooted($value)) {
        return Join-Path $Root $value.TrimStart('\')
    }

    if (Test-Path -LiteralPath $value) {
        return $value
    }

    $needle = "\$ProjectLeaf\"
    $position = $value.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase)
    if ($position -ge 0) {
        return Join-Path $Root $value.Substring($position + $needle.Length)
    }

    return $value
}

$ProjectRoot = Find-ProjectRoot
$ProjectLeaf = Split-Path -Path $ProjectRoot -Leaf
$TrackerFolder = Join-Path $ProjectRoot "tracker_files"
$BundleFolder = Join-Path $TrackerFolder "thread_upload_bundles"

if (-not (Test-Path -LiteralPath $TrackerFolder -PathType Container)) {
    New-Item -ItemType Directory -Path $TrackerFolder -Force | Out-Null
    throw "Created tracker folder: $TrackerFolder. Add a versioned tracker .md file and run again."
}

New-Item -ItemType Directory -Path $BundleFolder -Force | Out-Null

$trackers = Get-ChildItem -LiteralPath $TrackerFolder -File -Filter "*.md" | ForEach-Object {
    $key = Get-VersionKey $_.Name
    [pscustomobject]@{
        File = $_
        Major = $key.Major
        Minor = $key.Minor
        Patch = $key.Patch
    }
}

if ($TrackerName) {
    $selected = $trackers |
        Where-Object { $_.File.Name -eq $TrackerName } |
        Select-Object -First 1

    if ($null -eq $selected) {
        throw "Tracker not found: $TrackerName"
    }
}
else {
    $selected = $trackers |
        Sort-Object Major, Minor, Patch -Descending |
        Select-Object -First 1
}

if ($null -eq $selected) {
    throw "No tracker .md files found in: $TrackerFolder"
}

$trackerPath = $selected.File.FullName
$trackerText = Get-Content -LiteralPath $trackerPath -Raw -Encoding UTF8

$filePaths = New-Object 'System.Collections.Generic.List[string]'
$knownPaths = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)

function Add-FilePath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    $full = [System.IO.Path]::GetFullPath($Path)
    if ($knownPaths.Add($full)) {
        [void]$filePaths.Add($full)
    }
}

Add-FilePath $trackerPath

$requiredFilesHeader = [regex]::Match(
    $trackerText,
    '(?ms)^## Files required for implementation\s*\r?\n\r?\n```(?:text)?\s*\r?\n(.*?)\r?\n```'
)

if (-not $requiredFilesHeader.Success) {
    $requiredFilesHeader = [regex]::Match(
        $trackerText,
        '(?ms)^## Required files for next thread\s*\r?\n\r?\n```(?:text)?\s*\r?\n(.*?)\r?\n```'
    )
}

if ($requiredFilesHeader.Success) {
    $requiredFilesHeader.Groups[1].Value -split "`r?`n" | ForEach-Object {
        $candidate = $_.Trim()
        if ($candidate -match '\.(py|ps1|md|txt|json|toml|yaml|yml|bat)$') {
            Add-FilePath (Resolve-ProjectPath -RawPath $candidate -Root $ProjectRoot -ProjectLeaf $ProjectLeaf)
        }
    }
}

$allPathPatterns = @(
    '(?m)^\s*-\s+`?([A-Za-z]:\\[^`\r\n]+|(?:[A-Za-z0-9_. -]+[\\/])+[A-Za-z0-9_. -]+\.(?:py|ps1|md|txt|json|toml|yaml|yml|bat))`?\s*$',
    '(?m)^\s*`([A-Za-z]:\\[^`\r\n]+|(?:[A-Za-z0-9_. -]+[\\/])+[A-Za-z0-9_. -]+\.(?:py|ps1|md|txt|json|toml|yaml|yml|bat))`\s*$',
    '(?m)^\s*((?:[A-Za-z0-9_. -]+[\\/])+[A-Za-z0-9_. -]+\.(?:py|ps1|md|txt|json|toml|yaml|yml|bat))\s*$'
)

foreach ($pattern in $allPathPatterns) {
    foreach ($match in [regex]::Matches($trackerText, $pattern)) {
        Add-FilePath (Resolve-ProjectPath -RawPath $match.Groups[1].Value -Root $ProjectRoot -ProjectLeaf $ProjectLeaf)
    }
}

$separator = "=" * 100
$subSeparator = "-" * 100
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$version = if ($selected.Major -ge 0) {
    "v$($selected.Major).$($selected.Minor).$($selected.Patch)"
}
else {
    "unversioned"
}
$bundlePath = Join-Path $BundleFolder "${version}_thread_upload_bundle_${stamp}.txt"

$commonPrompt = @"
Read the uploaded QuantumTrade19 thread bundle completely before making changes.

1. Treat the LATEST TRACKER and its continuation prompt inside the bundle as the current phase instructions.
2. Treat every BEGIN FILE / END FILE section as the current source of truth for that file.
3. Do not ask me to paste or upload files already included in this bundle.
4. Follow the project rules: provide full downloadable replacement files only; include full paths; update the versioned tracker; preserve the build -> check -> debug -> re-check -> lock workflow; do not manually edit .web.
5. First tell me the exact next action, then proceed with the current incomplete phase.
"@

$output = New-Object System.Text.StringBuilder
[void]$output.AppendLine("QUANTUMTRADE19 - NEW THREAD UPLOAD BUNDLE")
[void]$output.AppendLine("Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')")
[void]$output.AppendLine("Detected project root: $ProjectRoot")
[void]$output.AppendLine("Latest tracker: $(Get-ProjectRelativePath -Path $trackerPath -Root $ProjectRoot)")
[void]$output.AppendLine($separator)
[void]$output.AppendLine("COMMON NEXT-THREAD PROMPT")
[void]$output.AppendLine($subSeparator)
[void]$output.AppendLine($commonPrompt.TrimEnd())
[void]$output.AppendLine($separator)
[void]$output.AppendLine("LATEST TRACKER")
[void]$output.AppendLine("SOURCE PATH: $(Get-ProjectRelativePath -Path $trackerPath -Root $ProjectRoot)")
[void]$output.AppendLine($subSeparator)
[void]$output.AppendLine($trackerText.TrimEnd())
[void]$output.AppendLine()

foreach ($filePath in $filePaths) {
    [void]$output.AppendLine($separator)

    if (Test-Path -LiteralPath $filePath -PathType Leaf) {
        $relative = Get-ProjectRelativePath -Path $filePath -Root $ProjectRoot
        $content = Get-Content -LiteralPath $filePath -Raw -Encoding UTF8

        [void]$output.AppendLine("BEGIN FILE: $relative")
        [void]$output.AppendLine("FULL PATH: $filePath")
        [void]$output.AppendLine("FILE TYPE: $([System.IO.Path]::GetExtension($filePath))")
        [void]$output.AppendLine($subSeparator)
        [void]$output.AppendLine($content.TrimEnd())
        [void]$output.AppendLine()
        [void]$output.AppendLine("END FILE: $relative")
    }
    else {
        [void]$output.AppendLine("MISSING FILE: $filePath")
        [void]$output.AppendLine("The latest tracker requested this file, but it was not found on this PC.")
    }

    [void]$output.AppendLine($separator)
    [void]$output.AppendLine()
}

[System.IO.File]::WriteAllText(
    $bundlePath,
    $output.ToString(),
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Detected project root: $ProjectRoot"
Write-Host "Latest tracker: $($selected.File.Name)"
Write-Host "Files included: $($filePaths.Count)"
Write-Host "Upload this file in the new thread:" -ForegroundColor Yellow
Write-Host $bundlePath -ForegroundColor Cyan
Write-Host ""
Write-Host "COPY AND PASTE THIS INTO THE NEW THREAD:" -ForegroundColor Yellow
Write-Host $separator -ForegroundColor DarkGray
Write-Host $commonPrompt.TrimEnd() -ForegroundColor White
Write-Host $separator -ForegroundColor DarkGray
