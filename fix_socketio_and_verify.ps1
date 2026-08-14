# FULL PATH: run from E:\QuantumTrade19 (project root)
# Cleans up the python-socketio/engineio conflict properly and verifies the fix.

.\venv\Scripts\Activate.ps1

Write-Host "--- Removing conflicting versions ---"
pip uninstall python-socketio python-engineio -y

Write-Host "--- Installing Reflex-required versions ---"
pip install "python-socketio>=5.12,<6"
pip install "python-engineio>=4.13.2,<5"

Write-Host "--- Re-freezing requirements.txt with correct pins ---"
pip freeze > requirements.txt

Write-Host "--- Verification ---"
pip show python-socketio | Select-String "Version"
pip show python-engineio | Select-String "Version"

Write-Host ""
Write-Host "Expected: python-socketio 5.16.x, python-engineio 4.13.x"
Write-Host "If both show correctly, delete install_coindcx_socketio_deps.ps1 -- it is now obsolete and will re-break this if run again."
Write-Host "Now restart the app: & '.\1. Start_QuantumTrade19.ps1'"
