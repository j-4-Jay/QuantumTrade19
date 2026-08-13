"""OTP_Delivery_Worker - generates short-lived one-time codes and delivers them via Telegram
bot(s) / Discord webhook(s).

PATH: engines/workers/security/otp_delivery_worker.py  (REPLACE ENTIRE FILE)

CHANGE (multi-channel support): "generate" and "deliver" are now separate operations.
Previously, send_via_telegram/send_via_discord generated a NEW code internally on every call -
harmless for one channel, but broadcasting to multiple channels of the same type would have
silently overwritten the stored code with each new call, so only the LAST channel's message
would actually verify. Now callers generate exactly one code and deliver the SAME code to every
enabled channel.
"""
from __future__ import annotations
import hashlib
import hmac
import random
import time
from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker

try:
    import requests
except ImportError:
    requests = None

OTP_VALID_SECONDS: int = 300  # 5 minutes


class OtpDeliveryWorker:
    def __init__(self, keystore: SecureKeyStorageWorker) -> None:
        self._keystore = keystore

    def _hash(self, code: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()

    def generate_code(self) -> str:
        """Create ONE new 6-digit OTP, store only its salted hash + expiry, return the plaintext.
        Call this once per Forgot-Password attempt, then deliver the same code to every channel."""
        code = f"{random.randint(0, 999999):06d}"
        salt = self._keystore.get_or_create_salt()
        self._keystore.set_secret("pending_otp_hash", self._hash(code, salt))
        self._keystore.set_secret("pending_otp_expires", str(int(time.time()) + OTP_VALID_SECONDS))
        return code

    def verify_otp(self, code: str) -> bool:
        stored_hash = self._keystore.get_secret("pending_otp_hash")
        expires = self._keystore.get_secret("pending_otp_expires")
        if not stored_hash or not expires or not code.strip():
            return False
        if int(time.time()) > int(expires):
            return False
        salt = self._keystore.get_or_create_salt()
        return hmac.compare_digest(stored_hash, self._hash(code.strip(), salt))

    def deliver_via_telegram(self, code: str, bot_token: str, chat_id: str) -> bool:
        """Send an already-generated `code` to one Telegram destination."""
        if requests is None or not bot_token or not chat_id:
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": f"QuantumTrade19 password reset code: {code} (valid 5 minutes)"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def deliver_via_discord(self, code: str, webhook_url: str) -> bool:
        """Send an already-generated `code` to one Discord webhook destination."""
        if requests is None or not webhook_url:
            return False
        try:
            resp = requests.post(
                webhook_url,
                json={"content": f"QuantumTrade19 password reset code: {code} (valid 5 minutes)"},
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def send_test_via_telegram(self, bot_token: str, chat_id: str) -> tuple[bool, str]:
        if requests is None:
            return False, "The 'requests' package is not installed in this venv. Run: pip install -r requirements.txt"
        if not bot_token:
            return False, "No bot token is saved yet for this channel."
        if not chat_id:
            return False, "No chat ID is saved yet for this channel."
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": "QuantumTrade19: this Telegram channel is connected successfully."},
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "Sent successfully - check Telegram."
            return False, f"Telegram API returned HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            return False, f"Network error contacting Telegram: {exc}"

    def send_test_via_discord(self, webhook_url: str) -> tuple[bool, str]:
        if requests is None:
            return False, "The 'requests' package is not installed in this venv. Run: pip install -r requirements.txt"
        if not webhook_url:
            return False, "No webhook URL is saved yet for this channel."
        try:
            resp = requests.post(webhook_url, json={"content": "QuantumTrade19: this Discord channel is connected successfully."}, timeout=10)
            if resp.status_code in (200, 204):
                return True, "Sent successfully - check Discord."
            return False, f"Discord webhook returned HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            return False, f"Network error contacting Discord: {exc}"
