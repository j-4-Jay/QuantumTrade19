@echo off
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" ("venv\Scripts\python.exe" "4c. Repair_Candles.py" --days 10 --write) else (python "4c. Repair_Candles.py" --days 10 --write)
pause
