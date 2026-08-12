@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   QuantumTrade19 - Project Scaffold Setup (v5)
echo ============================================

set ROOT=%~dp0

REM ---- Core engine tiers ----
mkdir "%ROOT%engines\workers\market_data"
mkdir "%ROOT%engines\workers\poi"
mkdir "%ROOT%engines\workers\setup_detection"
mkdir "%ROOT%engines\workers\confidence"
mkdir "%ROOT%engines\workers\risk_math"
mkdir "%ROOT%engines\workers\execution"
mkdir "%ROOT%engines\workers\alerts"
mkdir "%ROOT%engines\workers\security"
mkdir "%ROOT%engines\workers\journal"
mkdir "%ROOT%engines\workers\system_health"
mkdir "%ROOT%engines\workers\ui_experience"
mkdir "%ROOT%engines\workers\learning"
mkdir "%ROOT%engines\workers\intelligence"
mkdir "%ROOT%engines\monitors"
mkdir "%ROOT%engines\masters"

REM ---- UI layer ----
mkdir "%ROOT%ui\pages"
mkdir "%ROOT%ui\components"
mkdir "%ROOT%ui\theme"
mkdir "%ROOT%ui\sounds"

REM ---- Branding assets ----
mkdir "%ROOT%assets\branding"

REM ---- App infrastructure ----
mkdir "%ROOT%state"
mkdir "%ROOT%config"
mkdir "%ROOT%event_bus"

REM ---- Data storage (settings DB + historical candle data + manifests) ----
mkdir "%ROOT%data"
mkdir "%ROOT%data\historical"
mkdir "%ROOT%data\historical\1m"
mkdir "%ROOT%data\historical\5m"
mkdir "%ROOT%data\historical\15m"
mkdir "%ROOT%data\historical\htf"
mkdir "%ROOT%data\historical\manifests"
mkdir "%ROOT%data\historical\archive"

REM ---- Logs ----
mkdir "%ROOT%logs"

REM ---- Dedicated scratch/debug folder (safe to delete anytime) ----
mkdir "%ROOT%debug_temp"

REM ---- Versioned build-log summary folder (new in v5) ----
mkdir "%ROOT%docs\build_log"

REM ---- Tests mirror the engines/ tree ----
mkdir "%ROOT%tests\workers"
mkdir "%ROOT%tests\monitors"
mkdir "%ROOT%tests\masters"

echo.
echo Creating baseline files...

if not exist "%ROOT%requirements.txt" (
    (
        echo reflex
        echo pyotp
        echo qrcode
        echo keyring
        echo cryptography
        echo websockets
        echo requests
        echo python-dotenv
        echo apscheduler
        echo pandas
        echo numpy
        echo desktop-notifier
    ) > "%ROOT%requirements.txt"
)

if not exist "%ROOT%.gitignore" (
    (
        echo venv/
        echo __pycache__/
        echo *.pyc
        echo .env
        echo data/
        echo debug_temp/
        echo logs/
        echo .web/
    ) > "%ROOT%.gitignore"
)

if not exist "%ROOT%CHANGELOG.md" (
    echo # QuantumTrade19 - Changelog > "%ROOT%CHANGELOG.md"
    echo. >> "%ROOT%CHANGELOG.md"
    echo See docs\build_log\ for the full versioned per-module summary history. >> "%ROOT%CHANGELOG.md"
)

if not exist "%ROOT%docs\build_log\README.md" (
    echo # Build Log > "%ROOT%docs\build_log\README.md"
    echo. >> "%ROOT%docs\build_log\README.md"
    echo One file per locked module, named vX.Y.Z_ModuleName_Summary.md, added chronologically, never edited retroactively. >> "%ROOT%docs\build_log\README.md"
)

echo.
echo Creating Python virtual environment (venv)...
if not exist "%ROOT%venv" (
    python -m venv "%ROOT%venv"
)

echo.
echo ============================================
echo   Scaffold complete.
echo   Next: run "1. Start_QuantumTrade19.ps1" from PowerShell.
echo ============================================
pause
