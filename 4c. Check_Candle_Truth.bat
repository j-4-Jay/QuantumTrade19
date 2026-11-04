@echo off
cd /d "%~dp0"
venv\Scripts\python.exe debug_temp\check_candle_truth.py
pause
