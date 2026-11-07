@echo off
rem 4c. Record_Candle_Check.bat - FT-H.37 read-only recorder. Start the app first.
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "4c. Record_Candle_Check.py" B-ETH_USDT 3
) else (
  python "4c. Record_Candle_Check.py" B-ETH_USDT 3
)
echo.
pause
