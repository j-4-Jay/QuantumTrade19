# FULL PATH: D:\QuantumTrade19\1a. Start_QuantumTrade19_Clean.ps1
# NEW launcher (status row FT-H.24). The working "1. Start_QuantumTrade19.ps1" is NOT changed.
# What it does differently:
#   - clean colored start screen with numbered stages
#   - repeated console messages are collapsed: the same message shows ONCE with a counter (x5) at the right
#   - Python tracebacks are always shown in full (never collapsed)
#   - everything the app prints is still saved word for word in logs\console_full_<time>.log
#   - ready panel with the app and backend addresses
# Run it the same way as the old one:  & '.\1a. Start_QuantumTrade19_Clean.ps1'
# ASCII only in this file on purpose (no encoding problems in Windows PowerShell 5.1).

$ErrorActionPreference = "Stop"

$script:Esc = [char]27
$script:UseAnsi = $false
$script:Cols = 100
$script:OkMark = "OK"
$script:LiveText = $null
$script:LiveKey = ""
$script:LiveCount = 0
$script:LiveRgb = @(150, 170, 200)
$script:LiveFb = "Gray"
$script:Seen = @{}
$script:FirstText = @{}
$script:TotalRaw = 0
$script:Shown = 0
$script:Collapsed = 0
$script:InTrace = $false
$script:InRadix = $false
$script:RadixLines = 0
$script:AppUrl = ""
$script:BackendUrl = ""
$script:ReadyShown = $false
$script:RawWriter = $null
$script:Clock = [System.Diagnostics.Stopwatch]::StartNew()

function Initialize-Terminal {
    try { $script:Cols = [Math]::Max(60, $Host.UI.RawUI.WindowSize.Width - 2) } catch { $script:Cols = 100 }
    try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
    if ($env:WT_SESSION -or $env:TERM_PROGRAM -eq "vscode" -or $env:ANSICON -or $env:ConEmuANSI -eq "ON") {
        $script:UseAnsi = $true
    } else {
        try {
            if (-not ([System.Management.Automation.PSTypeName]"QtVt.Native").Type) {
                Add-Type -Namespace QtVt -Name Native -MemberDefinition @"
[DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr GetStdHandle(int h);
[DllImport("kernel32.dll", SetLastError = true)] public static extern bool GetConsoleMode(IntPtr h, out uint m);
[DllImport("kernel32.dll", SetLastError = true)] public static extern bool SetConsoleMode(IntPtr h, uint m);
"@
            }
            $handle = [QtVt.Native]::GetStdHandle(-11)
            [uint32]$mode = 0
            if ([QtVt.Native]::GetConsoleMode($handle, [ref]$mode)) {
                if ([QtVt.Native]::SetConsoleMode($handle, ($mode -bor 4))) { $script:UseAnsi = $true }
            }
        } catch {}
    }
    if ($script:UseAnsi) { $script:OkMark = [string][char]0x2714 }
}

function Write-Color {
    param([string]$Text, [int[]]$Rgb, [string]$Fb = "Gray", [switch]$NoNewline)
    if ($script:UseAnsi -and $Rgb -and $Rgb.Count -eq 3) {
        $s = "$($script:Esc)[38;2;$($Rgb[0]);$($Rgb[1]);$($Rgb[2])m$Text$($script:Esc)[0m"
        if ($NoNewline) { Write-Host $s -NoNewline } else { Write-Host $s }
    } else {
        if ($NoNewline) { Write-Host $Text -NoNewline -ForegroundColor $Fb } else { Write-Host $Text -ForegroundColor $Fb }
    }
}

function Write-Gradient {
    param([string]$Text, [int[]]$From, [int[]]$To)
    if (-not $script:UseAnsi) { Write-Host $Text -ForegroundColor Cyan; return }
    $sb = New-Object System.Text.StringBuilder
    $n = [Math]::Max(1, $Text.Length - 1)
    for ($i = 0; $i -lt $Text.Length; $i++) {
        $t = $i / $n
        $r = [int]($From[0] + ($To[0] - $From[0]) * $t)
        $g = [int]($From[1] + ($To[1] - $From[1]) * $t)
        $b = [int]($From[2] + ($To[2] - $From[2]) * $t)
        [void]$sb.Append("$($script:Esc)[38;2;${r};${g};${b}m")
        [void]$sb.Append($Text[$i])
    }
    [void]$sb.Append("$($script:Esc)[0m")
    Write-Host $sb.ToString()
}

function Write-Banner {
    Write-Host ""
    Write-Gradient "  ============================================================" @(0, 200, 255) @(170, 90, 255)
    Write-Gradient "    Q U A N T U M   T R A D E   1 9" @(0, 220, 255) @(200, 110, 255)
    Write-Color "    Premium trading software  |  clean launcher" @(140, 150, 180) "DarkGray"
    Write-Gradient "  ============================================================" @(170, 90, 255) @(0, 200, 255)
    Write-Host ""
}

function Write-Stage {
    param([int]$N, [int]$Total, [string]$Name, [string]$Detail)
    Write-Color ("  [{0}/{1}] " -f $N, $Total) @(110, 120, 150) "DarkGray" -NoNewline
    Write-Color $Name.PadRight(27) @(230, 235, 255) "White" -NoNewline
    Write-Color ($script:OkMark + " ") @(80, 230, 150) "Green" -NoNewline
    Write-Color $Detail @(140, 150, 175) "DarkGray"
}

function Show-Live {
    if ($null -eq $script:LiveText) { return }
    $suffix = ""
    # no repeat counter (Jay 02-11-2026): only unique messages are shown
    $room = $script:Cols - $suffix.Length - 4
    $msg = $script:LiveText
    if ($msg.Length -gt $room) { $msg = $msg.Substring(0, [Math]::Max(0, $room - 3)) + "..." }
    $pad = " " * [Math]::Max(1, $script:Cols - 3 - $msg.Length - $suffix.Length)
    Write-Host "`r" -NoNewline
    Write-Color ("  " + $msg) $script:LiveRgb $script:LiveFb -NoNewline
    Write-Host $pad -NoNewline
    if ($suffix -ne "") { Write-Color $suffix @(255, 170, 60) "Yellow" -NoNewline }
}

function Close-Live {
    if ($null -ne $script:LiveText) {
        Show-Live
        Write-Host ""
        $script:LiveText = $null
        $script:LiveKey = ""
        $script:LiveCount = 0
    }
}

function Show-Raw {
    param([string]$Text, [int[]]$Rgb, [string]$Fb)
    Close-Live
    Write-Color ("  " + $Text) $Rgb $Fb
    $script:Shown++
}

function Get-MessageKey {
    param([string]$Text)
    $k = $Text
    $k = $k -replace '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '#'
    $k = $k -replace '\b0x[0-9a-fA-F]+\b', '#'
    $k = $k -replace '\d+(\.\d+)?', '#'
    return $k.Trim().ToLowerInvariant()
}

function Test-DropLine {
    param([string]$Text)
    if ($Text -match 'Warning: Attempting to send delta to disconnected client') { return $true }
    if ($Text -match 'Windows Subsystem for Linux \(WSL\) is recommended') { return $true }
    if ($Text -match 'DeprecationWarning: Implicit Radix Themes enablement') { $script:InRadix = $true; $script:RadixLines = 0; return $true }
    if ($script:InRadix) {
        $script:RadixLines++
        if ($Text -match 'reflex_components_radix[\\/]plugin\.py:\d+\)') { $script:InRadix = $false; return $true }
        if ($script:RadixLines -ge 25) { $script:InRadix = $false; return $false }
        return $true
    }
    return $false
}

function Show-Ready {
    if ($script:ReadyShown -or $script:AppUrl -eq "" -or $script:BackendUrl -eq "") { return }
    $script:ReadyShown = $true
    Close-Live
    $secs = [int]$script:Clock.Elapsed.TotalSeconds
    $line = "  +--------------------------------------------------------------+"
    Write-Host ""
    Write-Color $line @(60, 220, 150) "Green"
    Write-Color ("  |  READY   App      " + $script:AppUrl).PadRight(65) @(255, 255, 255) "White" -NoNewline
    Write-Color "|" @(60, 220, 150) "Green"
    Write-Color ("  |          Backend  " + $script:BackendUrl).PadRight(65) @(190, 205, 235) "Gray" -NoNewline
    Write-Color "|" @(60, 220, 150) "Green"
    Write-Color ("  |          Started in " + $secs + " s     Ctrl+C stops the app").PadRight(65) @(140, 150, 175) "DarkGray" -NoNewline
    Write-Color "|" @(60, 220, 150) "Green"
    Write-Color $line @(60, 220, 150) "Green"
    Write-Host ""
}

function Receive-Line {
    param([string]$Raw)
    $script:TotalRaw++
    if ($script:RawWriter) { try { $script:RawWriter.WriteLine($Raw) } catch {} }
    $text = [regex]::Replace($Raw, '\x1b\[[0-9;?]*[ -/]*[@-~]', '')
    $text = $text.TrimEnd("`r", "`n")
    if ($text.Trim().Length -eq 0) { return }
    if (Test-DropLine $text) { return }

    if ($text -match '^\s*Traceback \(most recent call last\)') {
        $script:InTrace = $true
        Show-Raw $text @(255, 90, 90) "Red"
        return
    }
    if ($script:InTrace) {
        Show-Raw $text @(255, 120, 120) "Red"
        if ($text -notmatch '^\s') { $script:InTrace = $false }
        return
    }

    if ($text -match 'App running at:\s*(\S+)') { $script:AppUrl = $Matches[1]; Show-Ready; return }
    if ($text -match 'Backend running at:\s*(\S+)') { $script:BackendUrl = $Matches[1]; Show-Ready; return }

    $rgb = @(150, 170, 200); $fb = "Gray"
    if ($text -match '(?i)\b(error|exception|fatal|failed|critical)\b') { $rgb = @(255, 90, 90); $fb = "Red" }
    elseif ($text -match '(?i)\bwarn(ing)?\b') { $rgb = @(255, 200, 60); $fb = "Yellow" }
    elseif ($text -match '(?i)^\s*(compiling|installing|downloading|resolving)\b') { $rgb = @(170, 120, 255); $fb = "Magenta" }

    if ($text -match '(?i)^\s*(compiling|installing|downloading|resolving)\b') {
        if ($script:LiveKey -ne "progress") { Close-Live; $script:LiveKey = "progress"; $script:Shown++ }
        $script:LiveText = $text.Trim()
        $script:LiveCount = 1
        $script:LiveRgb = $rgb; $script:LiveFb = $fb
        Show-Live
        return
    }

    $key = Get-MessageKey $text
    if ($key -eq $script:LiveKey) {
        $script:LiveCount++
        $script:Seen[$key] = $script:Seen[$key] + 1
        $script:Collapsed++
        Show-Live
        return
    }
    if ($script:Seen.ContainsKey($key)) {
        $script:Seen[$key] = $script:Seen[$key] + 1
        $script:Collapsed++
        return
    }
    Close-Live
    $script:Seen[$key] = 1
    $script:FirstText[$key] = $text.Trim()
    $script:LiveKey = $key
    $script:LiveText = $text.Trim()
    $script:LiveCount = 1
    $script:LiveRgb = $rgb; $script:LiveFb = $fb
    $script:Shown++
    Show-Live
}

function Show-Summary {
    Close-Live
    Write-Host ""
    Write-Color ("  Session: {0} lines received, {1} shown (repeats hidden; full text is in the console log)." -f $script:TotalRaw, $script:Shown) @(140, 150, 175) "DarkGray"
    $top = $script:Seen.GetEnumerator() | Where-Object { $_.Value -gt 1 } | Sort-Object Value -Descending | Select-Object -First 5
    foreach ($item in $top) {
        $label = $script:FirstText[$item.Key]
        if ($label.Length -gt 70) { $label = $label.Substring(0, 67) + "..." }
        $null = $label
    }
}

function Stop-ChildProcessTree {
    param([int]$ParentId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ChildProcessTree -ParentId $child.ProcessId
        try { Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
}

function Reset-ConsoleInputMode {
    try {
        if (-not ([System.Management.Automation.PSTypeName]"Win32NativeConsole.Handles").Type) {
            Add-Type -Namespace Win32NativeConsole -Name Handles -MemberDefinition @"
[DllImport("kernel32.dll", SetLastError = true)]
public static extern IntPtr GetStdHandle(int nStdHandle);

[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);
"@
        }
        $defaultMode = 0x0001 -bor 0x0002 -bor 0x0004 -bor 0x0010 -bor 0x0020 -bor 0x0040 -bor 0x0080
        $handle = [Win32NativeConsole.Handles]::GetStdHandle(-10)
        if ($handle -ne [IntPtr]::Zero) { [void][Win32NativeConsole.Handles]::SetConsoleMode($handle, [uint32]$defaultMode) }
        [Console]::TreatControlCAsInput = $false
    } catch {}
}

function Invoke-QuantumTrade19CleanStart {
    $root = $PSScriptRoot
    $venvPath = Join-Path $root "venv"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    $flagFile = Join-Path $venvPath "installed.flag"
    $requirementsFile = Join-Path $root "requirements.txt"
    $logsDir = Join-Path $root "logs"
    $total = 5

    Initialize-Terminal
    Write-Banner

    if (-not (Test-Path -LiteralPath $venvPath)) {
        Write-Color "  No venv found. Creating one now..." @(255, 200, 60) "Yellow"
        python -m venv $venvPath
    }
    if (-not (Test-Path -LiteralPath $activateScript)) { throw "Virtual-environment activation file was not created: $activateScript" }

    $venvAlreadyActive = $env:VIRTUAL_ENV -and (
        (Resolve-Path -LiteralPath $env:VIRTUAL_ENV -ErrorAction SilentlyContinue).Path -eq
        (Resolve-Path -LiteralPath $venvPath -ErrorAction SilentlyContinue).Path
    )
    if ($venvAlreadyActive) {
        Write-Stage 1 $total "Virtual environment" "already active"
    } else {
        . $activateScript
        Write-Stage 1 $total "Virtual environment" "activated"
    }

    $needsInstall = -not (Test-Path -LiteralPath $flagFile)
    if (-not $needsInstall -and (Test-Path -LiteralPath $requirementsFile)) {
        $needsInstall = (Get-Item -LiteralPath $requirementsFile).LastWriteTime -gt (Get-Item -LiteralPath $flagFile).LastWriteTime
    }
    if ($needsInstall) {
        Write-Color "  Installing dependencies (first run or requirements.txt changed)..." @(255, 200, 60) "Yellow"
        $previous = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $pipOut = & python -m pip install -r $requirementsFile 2>&1
        $pipExit = $LASTEXITCODE
        $ErrorActionPreference = $previous
        if ($pipExit -ne 0) {
            $pipOut | Select-Object -Last 15 | ForEach-Object { Write-Color ("  " + $_) @(255, 90, 90) "Red" }
            throw "Dependency installation failed."
        }
        New-Item -ItemType File -Path $flagFile -Force | Out-Null
        Write-Stage 2 $total "Dependencies" "installed"
    } else {
        Write-Stage 2 $total "Dependencies" "up to date"
    }

    $reflexCommand = Get-Command reflex -ErrorAction SilentlyContinue
    if (-not $reflexCommand) {
        throw ("The 'reflex' command was not found on PATH after activating the venv at: " + $venvPath +
               ". Delete the 'venv' folder and '" + $flagFile + "', then run this script again.")
    }
    Write-Stage 3 $total "Reflex engine" "found"

    if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }
    try {
        Get-ChildItem -LiteralPath $logsDir -Filter "console_full_*.log" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 |
            ForEach-Object { try { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop } catch {} }
    } catch {}
    $rawLog = Join-Path $logsDir ("console_full_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
    $script:RawWriter = [System.IO.StreamWriter]::new($rawLog, $false, [System.Text.Encoding]::UTF8)
    $script:RawWriter.AutoFlush = $true
    Write-Stage 4 $total "Full console log" ("logs\" + (Split-Path -Leaf $rawLog))

    Set-Location $root
    Write-Stage 5 $total "Launching QuantumTrade19" "starting Reflex..."
    Write-Host ""

    $queue = New-Object 'System.Collections.Concurrent.ConcurrentQueue[string]'
    $exitCode = 0
    $proc = $null
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $reflexCommand.Source
        $psi.Arguments = "run"
        $psi.WorkingDirectory = $root
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.RedirectStandardInput = $true
        $psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"
        $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -MessageData $queue -Action {
            if ($null -ne $Event.SourceEventArgs.Data) { $Event.MessageData.Enqueue([string]$Event.SourceEventArgs.Data) }
        } | Out-Null
        Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -MessageData $queue -Action {
            if ($null -ne $Event.SourceEventArgs.Data) { $Event.MessageData.Enqueue([string]$Event.SourceEventArgs.Data) }
        } | Out-Null

        [void]$proc.Start()
        $proc.StandardInput.Close()
        $proc.BeginOutputReadLine()
        $proc.BeginErrorReadLine()

        $line = $null
        while (-not $proc.HasExited) {
            $count = 0
            while ($count -lt 300 -and $queue.TryDequeue([ref]$line)) { Receive-Line $line; $count++ }
            Start-Sleep -Milliseconds 100
        }
        Start-Sleep -Milliseconds 400
        while ($queue.TryDequeue([ref]$line)) { Receive-Line $line }
        $exitCode = $proc.ExitCode
        if ($exitCode -ne 0) {
            Close-Live
            Write-Color ("  Reflex exited with code " + $exitCode + ". Full output: " + $rawLog) @(255, 90, 90) "Red"
        }
    }
    finally {
        Close-Live
        Write-Host ""
        Write-Color "  Shutting down: cleaning up background processes..." @(255, 200, 60) "Yellow"
        try { if ($proc -and -not $proc.HasExited) { $proc.Kill($true) } } catch {}
        Get-EventSubscriber -ErrorAction SilentlyContinue | Unregister-Event -ErrorAction SilentlyContinue
        Stop-ChildProcessTree -ParentId $PID
        Start-Sleep -Milliseconds 300
        try { $Host.UI.RawUI.FlushInputBuffer() } catch {}
        Reset-ConsoleInputMode
        try { if ($script:RawWriter) { $script:RawWriter.Dispose() } } catch {}
        Show-Summary
        Write-Color ("  " + $script:OkMark + " Cleanup complete.") @(80, 230, 150) "Green"
    }
    return $exitCode
}

try {
    $finalExitCode = Invoke-QuantumTrade19CleanStart
    exit $finalExitCode
}
catch {
    Write-Host ""
    Write-Host "  ============================================" -ForegroundColor Red
    Write-Host "   QuantumTrade19 FAILED TO START" -ForegroundColor Red
    Write-Host "  ============================================" -ForegroundColor Red
    Write-Host ("  " + $_.Exception.Message) -ForegroundColor Red
    Write-Host ""
    Write-Host ($_ | Out-String) -ForegroundColor Yellow
    Write-Host "  Press Enter to close this window..." -ForegroundColor Cyan
    [void](Read-Host)
    exit 1
}
