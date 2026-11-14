@echo off
cd /d "%~dp0"
echo QT19 read-only candle stream probe. Keep the app running normally. No orders or database writes.
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "4c. Probe_Candle_Stream.py" --symbol B-ETH_USDT --minutes 20
) else (
  python "4c. Probe_Candle_Stream.py" --symbol B-ETH_USDT --minutes 20
)
echo.
echo Copy the printed summary and send it. Raw file stays in Debug (machine-local).
pause
