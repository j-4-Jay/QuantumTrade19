@echo off
rem FT-H.37 observer launcher v1.0.0. Start the app first.
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo STOP: project venv Python not found.
  pause
  exit /b 1
)
"venv\Scripts\python.exe" "4c. Validate_Settle_5m15m.py"
if errorlevel 1 echo STOP: observer failed. Send the error; do not rerun automatically.
pause
