"""Run: python Reset_Registration.py -- wipes stale local credentials so Registration reappears."""
import sys
try:
    import keyring
except ImportError:
    print("pip install keyring"); sys.exit(1)
SERVICE = "QuantumTrade19"
KEYS = ("auth_username","auth_password_hash","auth_salt","totp_secret","recovery_code_hash")
removed = []
for k in KEYS:
    try:
        keyring.delete_password(SERVICE, k); removed.append(k)
    except Exception:
        pass
print(f"Removed: {removed or 'none found'}")
