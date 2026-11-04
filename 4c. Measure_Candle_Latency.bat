@echo off
cd /d "%~dp0"
venv\Scripts\python.exe debug_temp\measure_candle_latency.py
pause
