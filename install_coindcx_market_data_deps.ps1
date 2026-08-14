# FULL PATH: run from E:\QuantumTrade19 (project root)
# Replaces the earlier install_coindcx_socketio_deps.ps1 -- that approach is
# now abandoned because it conflicts with Reflex. This installs the ONLY
# dependency the corrected coindcx_socket_transport.py needs.

.\venv\Scripts\Activate.ps1

# Step 1: revert the earlier conflicting downgrade (skip if you already ran revert_socketio_conflict.ps1)
pip uninstall python-socketio python-engineio -y
pip install "python-socketio>=5.12,<6"
pip install "python-engineio>=4.13.2,<5"

# Step 2: the only new dependency File 02's real WS transport needs
pip install websocket-client

pip freeze > requirements.txt

Write-Host "Reflex-compatible python-socketio/engineio restored."
Write-Host "websocket-client installed for the CoinDCX raw EIO3 transport."
Write-Host "requirements.txt re-frozen."
