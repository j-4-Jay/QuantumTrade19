@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
 echo STOP: project venv Python not found. No install attempted.
 pause
 exit /b 1
)
"venv\Scripts\python.exe" "4c. Diagnose_CSV_Anchor.py" %*
set "RC=%ERRORLEVEL%"
echo.
echo Send the printed diagnosis. No project data or request has been changed.
pause
exit /b %RC%
