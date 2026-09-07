@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp07_collect.from.projectFolder.ps1"
echo.
pause
