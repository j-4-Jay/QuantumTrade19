# PATH: state\1_Split_AppState.ps1
# QuantumTrade19 - AppState logical split, v0.3.3-prep
# Run from the project root. This script creates a backup and writes a new
# state\app_state.py facade plus five numbered state modules.
# It does NOT delete the original implementation; the exact original is saved
# under state\backups\ before any source is replaced.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$stateRoot = Join-Path $projectRoot "state"
$sourcePath = Join-Path $stateRoot "app_state.py"
$backupRoot = Join-Path $stateRoot "backups"
$moduleRoot = Join-Path $stateRoot "app_state_parts"
$hashExpected = "C0184C1A9715C790441F8650F06BF1EFBA18BE0BD17CF893C528B9981C6DF69A"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Missing source file: $sourcePath"
}

$currentHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
if ($currentHash -ne $hashExpected) {
    throw "Safety stop: state\app_state.py does not match the approved source hash. Expected $hashExpected but found $currentHash. No files were changed."
}

New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
New-Item -ItemType Directory -Force -Path $moduleRoot | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupRoot "app_state_before_split_$stamp.py"
Copy-Item -LiteralPath $sourcePath -Destination $backupPath -Force

$source = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8

$marker = "class AppState(rx.State):"
$markerIndex = $source.IndexOf($marker, [System.StringComparison]::Ordinal)
if ($markerIndex -lt 0) {
    throw "Safety stop: could not find 'class AppState(rx.State):' in state\app_state.py. Backup exists at $backupPath."
}

$header = $source.Substring(0, $markerIndex)
$body = $source.Substring($markerIndex + $marker.Length)

function Get-MethodStartIndices([string]$Text) {
    $matches = [regex]::Matches($Text, '(?m)^    (?:@[^\r\n]+\r?\n(?:    [^\r\n]*\r?\n)*)?(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    return @($matches | ForEach-Object { $_.Index })
}

$starts = Get-MethodStartIndices $body
if ($starts.Count -lt 20) {
    throw "Safety stop: method parsing found only $($starts.Count) AppState methods. Backup exists at $backupPath."
}

$stateFieldsEnd = $starts[0]
$stateFields = $body.Substring(0, $stateFieldsEnd)
$methods = @()
for ($i = 0; $i -lt $starts.Count; $i++) {
    $start = $starts[$i]
    $end = if ($i -lt $starts.Count - 1) { $starts[$i + 1] } else { $body.Length }
    $methods += $body.Substring($start, $end - $start)
}

function Get-MethodName([string]$MethodText) {
    $match = [regex]::Match($MethodText, '(?m)^    (?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    if (-not $match.Success) {
        $match = [regex]::Match($MethodText, '(?m)^    @[^\r\n]+\r?\n    (?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    }
    if (-not $match.Success) { throw "Could not read an AppState method name." }
    return $match.Groups[1].Value
}

$groups = @{
    "01_core_shell" = New-Object System.Collections.Generic.List[string]
    "02_auth_security" = New-Object System.Collections.Generic.List[string]
    "03_market_dashboard" = New-Object System.Collections.Generic.List[string]
    "04_poi_settings" = New-Object System.Collections.Generic.List[string]
    "05_trading_panel" = New-Object System.Collections.Generic.List[string]
}

$tradingNames = @(
    "_chart_workspace_key", "_load_trading_panel_display_days", "set_trading_panel_symbol",
    "set_trading_panel_chart_tf", "set_trading_panel_display_days", "set_trading_panel_chart_theme",
    "refresh_trading_panel_chart", "poll_trading_panel_chart", "trading_panel_symbol_options",
    "trading_panel_symbol_info", "trading_panel_period"
)
$poiNames = @(
    "load_poi_settings", "toggle_poi_display", "toggle_poi_strategy", "toggle_poi_zone_source_tf",
    "_save_poi_visual_settings", "toggle_poi_show_labels", "toggle_poi_show_tooltips",
    "toggle_poi_show_source_tf_badge", "toggle_poi_show_logical_id", "toggle_poi_reduced_motion",
    "set_poi_line_transparency", "set_poi_zone_opacity", "poi_show_all", "poi_hide_all",
    "poi_enable_default_strategy", "poi_disable_all_strategy", "poi_reset_chart_filters",
    "poi_line_rows", "poi_zone_type_rows", "poi_zone_source_tf_rows"
)
$marketNames = @(
    "poll_ws_status", "poll_pinned_prices", "toggle_paper_live", "refresh_symbol_rows",
    "toggle_favorite", "set_deep_history_symbol", "set_deep_history_timeframe",
    "set_deep_history_target_days", "check_deep_history_ceiling", "refresh_deep_history_status",
    "start_deep_history_download", "cancel_deep_history_download", "delete_deep_history_data",
    "poll_deep_history_status", "open_detail_popup", "close_detail_popup",
    "trading_panel_symbol_options"
)
$coreNames = @(
    "on_load", "start_poi_monitor_background", "run_splash_sequence", "set_active_tab", "set_theme",
    "toggle_sound", "play_sound", "_pick_transition_effect", "_pick_tab_transition_effect",
    "toggle_transition_effect", "set_transition_mode", "toggle_tab_transition_effect",
    "set_tab_transition_mode", "theme_vars", "sidebar_tabs", "theme_options", "transition_effect_options"
)

foreach ($method in $methods) {
    $name = Get-MethodName $method
    if ($tradingNames -contains $name) {
        $groups["05_trading_panel"].Add($method)
    } elseif ($poiNames -contains $name) {
        $groups["04_poi_settings"].Add($method)
    } elseif ($marketNames -contains $name) {
        $groups["03_market_dashboard"].Add($method)
    } elseif ($coreNames -contains $name) {
        $groups["01_core_shell"].Add($method)
    } else {
        $groups["02_auth_security"].Add($method)
    }
}

$commonImport = @"
# Auto-generated by state\1_Split_AppState.ps1.
# Do not edit this file directly. Edit the matching source part and rerun the
# assembly script produced by a future refactor phase.
from __future__ import annotations

"@

$partPaths = @()
$groupIndex = 1
foreach ($groupName in @("01_core_shell", "02_auth_security", "03_market_dashboard", "04_poi_settings", "05_trading_panel")) {
    $fileName = "$groupName.py"
    $filePath = Join-Path $moduleRoot $fileName
    $methodText = [string]::Join("`r`n", $groups[$groupName])
    $content = $commonImport + "# Logical section: $groupName`r`n`r`n" + $methodText.Trim() + "`r`n"
    Set-Content -LiteralPath $filePath -Value $content -Encoding UTF8
    $partPaths += $filePath
    $groupIndex++
}

$initPath = Join-Path $moduleRoot "__init__.py"
Set-Content -LiteralPath $initPath -Value "# QuantumTrade19 AppState logical source parts.`r`n" -Encoding UTF8

$assembledMethods = [string]::Join("`r`n", $methods)
$newAppState = $header + @"
class AppState(rx.State):
$stateFields
$assembledMethods
"@
Set-Content -LiteralPath $sourcePath -Value $newAppState -Encoding UTF8

$compileResult = & python -m py_compile $sourcePath 2>&1
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath $backupPath -Destination $sourcePath -Force
    throw "Split verification failed. The original app_state.py was restored automatically. Python output: $compileResult"
}

Write-Host "SUCCESS: AppState was backed up and logically split." -ForegroundColor Green
Write-Host "Backup: $backupPath"
Write-Host "Active facade: $sourcePath"
Write-Host "Logical part files: $moduleRoot"
Write-Host "IMPORTANT: The app continues using state\app_state.py. The five files are an organized reference snapshot only in this first safe split pass. A later refactor will convert them into executable mixins without risking the current running app."
