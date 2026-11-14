@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
 echo STOP: project venv Python not found. No install attempted.
 pause
 exit /b 1
)
set "PYTHONDONTWRITEBYTECODE=1"
"venv\Scripts\python.exe" -B "4c. Analyze_Candle_Shadow.py"
if errorlevel 1 (
 echo STOP: analysis failed. Send complete output; do not assume completion.
 pause
 exit /b 1
)
pause
exit /b 0
