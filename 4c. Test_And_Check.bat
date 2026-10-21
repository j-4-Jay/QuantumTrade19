@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
set "PY="
if exist "venv\Scripts\python.exe" set "PY="%~dp0venv\Scripts\python.exe""
if not defined PY if exist ".venv\Scripts\python.exe" set "PY="%~dp0.venv\Scripts\python.exe""
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3 was not found. Install Python 3 or create venv, then run this file again.
  pause
  exit /b 1
)
rem Runs the regression suite
%PY% "4. Project_Operations_Core.py" selftest
set "EC=%ERRORLEVEL%"
echo.
echo Finished with exit code %EC%.
pause
exit /b %EC%
