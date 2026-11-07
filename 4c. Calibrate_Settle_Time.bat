@echo off
rem 4c. Calibrate_Settle_Time.bat - FT-H.37 read-only settle-time calibration. Start the app first.
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "4c. Calibrate_Settle_Time.py" B-ETH_USDT 20
) else (
  python "4c. Calibrate_Settle_Time.py" B-ETH_USDT 20
)
echo.
pause
