@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Replace_From_Downloads.ps1"
echo.
pause
