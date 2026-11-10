@echo off
rem FT-H.37 offline evaluation launcher v1.0.0. Does not start measurements.
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo STOP: project venv Python not found.
  pause
  exit /b 1
)
"venv\Scripts\python.exe" -m pytest tests/test_settle_5m15m_observer.py -q -p no:cacheprovider
if errorlevel 1 goto failed
"venv\Scripts\python.exe" -m pytest tests -q -p no:cacheprovider
if errorlevel 1 goto failed
echo Evaluation finished. This is not live acceptance.
pause
exit /b 0
:failed
echo STOP: evaluation failed. Send the output; do not start measurement.
pause
exit /b 1
