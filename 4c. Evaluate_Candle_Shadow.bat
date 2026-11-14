@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
 echo STOP: project venv Python not found. No install attempted.
 pause
 exit /b 1
)
set "QT19_CANDLE_SHADOW="
"venv\Scripts\python.exe" -m pytest tests/test_candle_shadow_worker.py tests/test_candle_shadow_monitor_hooks.py tests/test_candle_stream_probe.py -q -p no:cacheprovider
if errorlevel 1 goto failed
echo Offline focused evaluation passed. This is NOT live acceptance or full regression verification.
pause
exit /b 0
:failed
echo STOP: focused evaluation failed. Do not start Shadow; send complete output.
pause
exit /b 1
