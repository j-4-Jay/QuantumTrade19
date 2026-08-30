# FULL PATH: D:\QuantumTrade19\1. Start_QuantumTrade19.ps1
# REPLACE THE ENTIRE EXISTING FILE WITH THIS FILE.
#
# CHANGE (this revision, per explicit request - no .bat wrapper):
# A .ps1 cannot bypass a Restricted execution policy from inside itself -
# Windows decides whether to run any of its lines at all before the script
# starts. That is a one-time Windows setting, not something any script
# content can work around. Run this ONCE, ever, in this or any PowerShell
# window:
#
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
#
# After that one-time command, `& '.\1. Start_QuantumTrade19.ps1'` works
# directly, with no wrapper file needed, forever.
#
# CHANGE (this revision, real fix): the whole script body is now wrapped in
# a top-level try/catch. Previously, if something failed inside the main
# try block (e.g. the `reflex` command not being found after a project
# folder move), the finally block's cleanup message printed but the actual
# error was easy to miss/scroll past, making it look like a silent, causeless
# exit. Now:
#   - Before launching, it explicitly checks that the `reflex` command is
#     resolvable in this venv and gives a clear, specific message if not.
#   - Any other uncaught error is now caught at the top level, printed in
#     full (message + full error record) in red, and the window pauses on
#     an actual error so it can never be missed again.
#
# Also unchanged from the previous revision: venv activation is skipped if
# a venv is already active in the current shell AND it's this exact
# project's venv (checked via $env:VIRTUAL_ENV).

$ErrorActionPreference = "Stop"

function Invoke-QuantumTrade19Start {
    $root = $PSScriptRoot
    $venvPath = Join-Path $root "venv"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    $flagFile = Join-Path $venvPath "installed.flag"
    $requirementsFile = Join-Path $root "requirements.txt"
    $logsDir = Join-Path $root "logs"

    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  QuantumTrade19 - Starting Application" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan

    if (-not (Test-Path -LiteralPath $venvPath)) {
        Write-Host "No venv found. Creating one now..." -ForegroundColor Yellow
        python -m venv $venvPath
    }

    if (-not (Test-Path -LiteralPath $activateScript)) {
        throw "Virtual-environment activation file was not created: $activateScript"
    }

    $venvAlreadyActive = $env:VIRTUAL_ENV -and (
        (Resolve-Path -LiteralPath $env:VIRTUAL_ENV -ErrorAction SilentlyContinue).Path -eq
        (Resolve-Path -LiteralPath $venvPath -ErrorAction SilentlyContinue).Path
    )

    if ($venvAlreadyActive) {
        Write-Host "Virtual environment already active." -ForegroundColor Green
    } else {
        Write-Host "Activating virtual environment..." -ForegroundColor Green
        . $activateScript
    }

    $needsInstall = -not (Test-Path -LiteralPath $flagFile)
    if (-not $needsInstall -and (Test-Path -LiteralPath $requirementsFile)) {
        $needsInstall = (Get-Item -LiteralPath $requirementsFile).LastWriteTime -gt (Get-Item -LiteralPath $flagFile).LastWriteTime
    }

    if ($needsInstall) {
        Write-Host "requirements.txt changed (or first run) -- installing dependencies..." -ForegroundColor Yellow
        python -m pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed."
        }
        New-Item -ItemType File -Path $flagFile -Force | Out-Null
        Write-Host "Dependencies installed and flag updated." -ForegroundColor Green
    } else {
        Write-Host "Dependencies already up to date." -ForegroundColor Green
    }

    $reflexCommand = Get-Command reflex -ErrorAction SilentlyContinue
    if (-not $reflexCommand) {
        throw (
            "The 'reflex' command was not found on PATH after activating the venv at:`n" +
            "  $venvPath`n" +
            "This usually means the venv's own Scripts folder was not put on PATH " +
            "correctly (common after moving/renaming the project folder), or reflex " +
            "is not actually installed in this venv. Try: `n" +
            "  1. Delete the 'venv' folder entirely.`n" +
            "  2. Delete '$flagFile' if it still exists.`n" +
            "  3. Run this script again - it will recreate the venv and reinstall everything fresh."
        )
    }

    if (-not (Test-Path -LiteralPath $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    # Best-effort cleanup of old leftover temp log files from previous runs.
    # Anything still locked by a leftover process is simply skipped - harmless,
    # since this run uses brand-new unique filenames anyway.
    Get-ChildItem -LiteralPath $logsDir -Filter "_console_std*.tmp.log" -ErrorAction SilentlyContinue | ForEach-Object {
        try { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop } catch {}
    }

    $runTag = "{0}_{1}" -f $PID, (Get-Date -Format "yyyyMMdd_HHmmss_fff")
    $stdOutFile = Join-Path $logsDir "_console_stdout_$runTag.tmp.log"
    $stdErrFile = Join-Path $logsDir "_console_stderr_$runTag.tmp.log"
    New-Item -ItemType File -Path $stdOutFile -Force | Out-Null
    New-Item -ItemType File -Path $stdErrFile -Force | Out-Null

    Write-Host "Launching QuantumTrade19..." -ForegroundColor Cyan
    Set-Location $root

    function Stop-ChildProcessTree {
        param([int]$ParentId)
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId" -ErrorAction SilentlyContinue
        foreach ($child in $children) {
            Stop-ChildProcessTree -ParentId $child.ProcessId
            try {
                Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
            } catch {}
        }
    }

    if (-not ([System.Management.Automation.PSTypeName]"Win32NativeConsole.Handles").Type) {
        Add-Type -Namespace Win32NativeConsole -Name Handles -MemberDefinition @"
[DllImport("kernel32.dll", SetLastError = true)]
public static extern IntPtr GetStdHandle(int nStdHandle);

[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);
"@
    }

    function Reset-ConsoleInputMode {
        try {
            $STD_INPUT_HANDLE       = -10
            $ENABLE_PROCESSED_INPUT = 0x0001
            $ENABLE_LINE_INPUT      = 0x0002
            $ENABLE_ECHO_INPUT      = 0x0004
            $ENABLE_MOUSE_INPUT     = 0x0010
            $ENABLE_INSERT_MODE     = 0x0020
            $ENABLE_QUICK_EDIT_MODE = 0x0040
            $ENABLE_EXTENDED_FLAGS  = 0x0080

            $defaultMode = $ENABLE_PROCESSED_INPUT -bor $ENABLE_LINE_INPUT -bor $ENABLE_ECHO_INPUT `
                -bor $ENABLE_MOUSE_INPUT -bor $ENABLE_INSERT_MODE -bor $ENABLE_QUICK_EDIT_MODE -bor $ENABLE_EXTENDED_FLAGS

            $handle = [Win32NativeConsole.Handles]::GetStdHandle($STD_INPUT_HANDLE)
            if ($handle -ne [IntPtr]::Zero) {
                [void][Win32NativeConsole.Handles]::SetConsoleMode($handle, [uint32]$defaultMode)
            }
            [Console]::TreatControlCAsInput = $false
        } catch {}
    }

    $insideRadixWarning = $false
    $radixWarningLineCount = 0
    $radixSafetyNoticeShown = $false
    $radixMaxLines = 25

    function Write-FilteredLine {
        param([string]$line)

        if ($line -match "Warning: Attempting to send delta to disconnected client") {
            return
        }
        if ($line -match 'Windows Subsystem for Linux \(WSL\) is recommended') {
            return
        }
        if ($line -match 'DeprecationWarning: Implicit Radix Themes enablement') {
            $script:insideRadixWarning = $true
            $script:radixWarningLineCount = 0
            return
        }
        if ($script:insideRadixWarning) {
            $script:radixWarningLineCount++
            if ($line -match 'reflex_components_radix[\\/]plugin\.py:\d+\)') {
                $script:insideRadixWarning = $false
                return
            }
            if ($script:radixWarningLineCount -ge $radixMaxLines) {
                $script:insideRadixWarning = $false
                if (-not $script:radixSafetyNoticeShown) {
                    Write-Host "[Start script notice] Radix deprecation filter did not find its expected closing line after $radixMaxLines lines - resuming normal output to avoid hiding real errors." -ForegroundColor Yellow
                    $script:radixSafetyNoticeShown = $true
                }
                Write-Host $line
                return
            }
            return
        }

        Write-Host $line
    }

    function Read-NewLines {
        param([string]$Path, [ref]$PosRef, [ref]$BufferRef)
        if (-not (Test-Path -LiteralPath $Path)) { return @() }
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            if ($fs.Length -le $PosRef.Value) { return @() }
            [void]$fs.Seek($PosRef.Value, [System.IO.SeekOrigin]::Begin)
            $reader = New-Object System.IO.StreamReader($fs)
            $chunk = $reader.ReadToEnd()
            $PosRef.Value = $fs.Position
            $combined = $BufferRef.Value + $chunk
            $parts = $combined -split "`n"
            if ($parts.Count -gt 0) {
                $BufferRef.Value = $parts[$parts.Count - 1]
                if ($parts.Count -gt 1) {
                    return $parts[0..($parts.Count - 2)]
                }
            }
            return @()
        } finally {
            $fs.Dispose()
        }
    }

    $stdoutPos = [int64]0
    $stdoutBuffer = ""
    $stderrPos = [int64]0
    $stderrBuffer = ""
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

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi

        $outWriter = [System.IO.StreamWriter]::new($stdOutFile, $false)
        $outWriter.AutoFlush = $true
        $errWriter = [System.IO.StreamWriter]::new($stdErrFile, $false)
        $errWriter.AutoFlush = $true

        Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action {
            if ($null -ne $Event.SourceEventArgs.Data) {
                $Event.MessageData.WriteLine($Event.SourceEventArgs.Data)
            }
        } -MessageData $outWriter | Out-Null

        Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -Action {
            if ($null -ne $Event.SourceEventArgs.Data) {
                $Event.MessageData.WriteLine($Event.SourceEventArgs.Data)
            }
        } -MessageData $errWriter | Out-Null

        [void]$proc.Start()
        $proc.StandardInput.Close()
        $proc.BeginOutputReadLine()
        $proc.BeginErrorReadLine()

        while (-not $proc.HasExited) {
            foreach ($line in (Read-NewLines -Path $stdOutFile -PosRef ([ref]$stdoutPos) -BufferRef ([ref]$stdoutBuffer))) {
                Write-FilteredLine ($line.TrimEnd("`r"))
            }
            foreach ($line in (Read-NewLines -Path $stdErrFile -PosRef ([ref]$stderrPos) -BufferRef ([ref]$stderrBuffer))) {
                Write-FilteredLine ($line.TrimEnd("`r"))
            }
            Start-Sleep -Milliseconds 200
        }

        Start-Sleep -Milliseconds 300
        foreach ($line in (Read-NewLines -Path $stdOutFile -PosRef ([ref]$stdoutPos) -BufferRef ([ref]$stdoutBuffer))) {
            Write-FilteredLine ($line.TrimEnd("`r"))
        }
        foreach ($line in (Read-NewLines -Path $stdErrFile -PosRef ([ref]$stderrPos) -BufferRef ([ref]$stderrBuffer))) {
            Write-FilteredLine ($line.TrimEnd("`r"))
        }

        $exitCode = $proc.ExitCode

        if ($exitCode -ne 0) {
            Write-Host ""
            Write-Host "[Start script notice] reflex exited with code $exitCode. Check the output above for the actual error." -ForegroundColor Red
        }
    }
    finally {
        Write-Host ""
        Write-Host "Shutting down: cleaning up background processes..." -ForegroundColor Yellow
        try {
            if ($proc -and -not $proc.HasExited) {
                $proc.Kill($true)
            }
        } catch {}
        Get-EventSubscriber -ErrorAction SilentlyContinue | Unregister-Event -ErrorAction SilentlyContinue
        Stop-ChildProcessTree -ParentId $PID
        Start-Sleep -Milliseconds 300
        try { $Host.UI.RawUI.FlushInputBuffer() } catch {}
        Reset-ConsoleInputMode
        Remove-Item -LiteralPath $stdOutFile, $stdErrFile -ErrorAction SilentlyContinue
        Write-Host "Cleanup complete." -ForegroundColor Green
    }

    return $exitCode
}

try {
    $finalExitCode = Invoke-QuantumTrade19Start
    exit $finalExitCode
}
catch {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  QuantumTrade19 FAILED TO START" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Full error detail:" -ForegroundColor Yellow
    Write-Host ($_ | Out-String) -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press Enter to close this window..." -ForegroundColor Cyan
    [void](Read-Host)
    exit 1
}
