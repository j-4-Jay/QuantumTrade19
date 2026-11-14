@echo off
setlocal
cd /d "%~dp0"
echo QT19 SHADOW observation only. Current feed and decisions are unchanged.
echo Stop any existing QT19 server before starting this launcher.
echo Evidence is capped under Debug\CandleShadow. Normal clean launch leaves Shadow off.
set "QT19_CANDLE_SHADOW=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp01a. Start_QuantumTrade19_Clean.ps1"
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
