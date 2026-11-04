@echo off
cd /d "%~dp0"
if not exist Debug mkdir Debug
venv\Scripts\python.exe -m pytest tests -q --tb=short --ignore=tests/monitors/test_poi_monitor_assembly.py > Debug\pytest_last.txt 2>&1
type Debug\pytest_last.txt
clip < Debug\pytest_last.txt
echo.
echo Result copied to clipboard. Paste it in the chat.
pause
