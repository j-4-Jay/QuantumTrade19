"""Security Monitor - groups the Security Workers behind one clean interface upward.

PATH: engines/monitors/security_monitor.py  (REPLACE ENTIRE FILE - fully overwrite, don't merge)

CHANGE (Module 01 gap-closure item 10): added is_device_trusted() / trust_this_device() /
clear_device_trust() - backs the "Remember this device" 60-day toggle on Login. login() now
skips the TOTP check entirely when the device is currently trusted, regardless of whether
TOTP is enabled on the account. Trust is stored via the OS keyring (same mechanism as the
TOTP secret), so it is machine-bound - a different machine never sees it.
"""
from __future__ import annotations
import time
from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.security.auth_login_worker import AuthLoginWorker
from engines.workers.security.totp_2fa_worker import Totp2FAWorker
from engines.workers.security.app_lock_worker import AppLockWorker
from engines.workers.security.otp_delivery_worker import OtpDeliveryWorker


DEVICE_TRUST_SECONDS: int = 60 * 24 * 60 * 60  # 60 days


class SecurityMonitor:
    def __init__(self, force_memory: bool = False) -> None:
        self.keystore = SecureKeyStorageWorker(force_memory=force_memory)
        self.persistence = SettingsPersistenceWorker()
        self.auth = AuthLoginWorker(self.keystore)
        self.totp = Totp2FAWorker(self.keystore)
        self.app_lock = AppLockWorker()
        self.otp = OtpDeliveryWorker(self.keystore)


    def is_first_run(self) -> bool:
        stored = self.keystore.get_secret("auth_username")
        return stored is None or not stored.strip()


    def is_totp_enabled(self) -> bool:
        return bool(self.persistence.load().get("totp_enabled", False))


    def register_credentials(self, username: str, password: str) -> bool:
        return self.auth.set_credentials(username, password)


    def begin_totp_enrollment(self, username: str) -> str:
        return self.totp.qr_code_data_uri(username)


    def confirm_totp_enrollment(self, code: str) -> bool:
        if not self.totp.verify(code):
            return False
        self.persistence.save({"totp_enabled": True})
        return True


    def disable_totp(self) -> None:
        self.persistence.save({"totp_enabled": False})


    # --- Generic settings passthrough ---
    def get_setting(self, key: str, default=None):
        return self.persistence.load().get(key, default)

    def set_setting(self, key: str, value) -> None:
        self.persistence.save({key: value})


    # --- Per-symbol setting interface (exercised for real in Module 02) ---
    def get_per_symbol_setting(self, symbol: str, key: str, default=None):
        return self.persistence.get_per_symbol_setting(symbol, key, default)

    def set_per_symbol_setting(self, symbol: str, key: str, value) -> None:
        self.persistence.set_per_symbol_setting(symbol, key, value)


    # --- Remember this device (60 days) ---
    def is_device_trusted(self) -> bool:
        trust_until = self.keystore.get_secret("device_trust_until")
        if not trust_until:
            return False
        try:
            return int(time.time()) < int(trust_until)
        except (TypeError, ValueError):
            return False

    def trust_this_device(self) -> None:
        trust_until = int(time.time()) + DEVICE_TRUST_SECONDS
        self.keystore.set_secret("device_trust_until", str(trust_until))

    def clear_device_trust(self) -> None:
        self.keystore.delete_secret("device_trust_until")


    def login(self, username: str, password: str, totp_code: str | None = None) -> bool:
        if not self.auth.verify(username, password):
            return False
        if self.is_totp_enabled() and not self.is_device_trusted():
            if not totp_code or not self.totp.verify(totp_code):
                return False
        self.app_lock.unlock()
        return True


    def lock_ui(self) -> None:
        self.app_lock.lock()


    def is_ui_locked(self) -> bool:
        return self.app_lock.is_locked()


    def touch_activity(self) -> None:
        self.app_lock.touch()


    # --- Telegram channel ---
    def is_telegram_enabled(self) -> bool:
        return bool(self.persistence.load().get("telegram_notify_enabled", False))


    def has_telegram_configured(self) -> bool:
        return bool(self.keystore.get_secret("telegram_bot_token")) and bool(self.keystore.get_secret("telegram_chat_id"))


    def set_telegram_config(self, bot_token: str, chat_id: str, enabled: bool) -> None:
        if bot_token.strip():
            self.keystore.set_secret("telegram_bot_token", bot_token.strip())
        if chat_id.strip():
            self.keystore.set_secret("telegram_chat_id", chat_id.strip())
        self.persistence.save({"telegram_notify_enabled": enabled})


    def send_test_telegram(self) -> tuple[bool, str]:
        return self.otp.send_test_via_telegram(
            self.keystore.get_secret("telegram_bot_token") or "",
            self.keystore.get_secret("telegram_chat_id") or "",
        )


    # --- Discord channel ---
    def is_discord_enabled(self) -> bool:
        return bool(self.persistence.load().get("discord_notify_enabled", False))


    def has_discord_configured(self) -> bool:
        return bool(self.keystore.get_secret("discord_webhook_url"))


    def set_discord_config(self, webhook_url: str, enabled: bool) -> None:
        if webhook_url.strip():
            self.keystore.set_secret("discord_webhook_url", webhook_url.strip())
        self.persistence.save({"discord_notify_enabled": enabled})


    def send_test_discord(self) -> tuple[bool, str]:
        return self.otp.send_test_via_discord(self.keystore.get_secret("discord_webhook_url") or "")


    # --- Forgot Password recovery methods ---
    def has_any_recovery_method(self) -> bool:
        if self.is_totp_enabled():
            return True
        if self.is_telegram_enabled() and self.has_telegram_configured():
            return True
        if self.is_discord_enabled() and self.has_discord_configured():
            return True
        return False


    def available_reset_methods(self) -> list[str]:
        methods: list[str] = []
        if self.is_totp_enabled():
            methods.append("totp")
        if self.is_telegram_enabled() and self.has_telegram_configured():
            methods.append("telegram")
        if self.is_discord_enabled() and self.has_discord_configured():
            methods.append("discord")
        return methods


    def send_forgot_otp(self, method: str) -> bool:
        if method == "telegram":
            return self.otp.send_via_telegram(
                self.keystore.get_secret("telegram_bot_token") or "",
                self.keystore.get_secret("telegram_chat_id") or "",
            )
        if method == "discord":
            return self.otp.send_via_discord(self.keystore.get_secret("discord_webhook_url") or "")
        return False


    def verify_identity_for_reset(self, method: str, code: str) -> bool:
        if method == "totp":
            return self.totp.verify(code)
        if method in ("telegram", "discord"):
            return self.otp.verify_otp(code)
        return False


    def reset_password(self, username: str, new_password: str) -> bool:
        return self.auth.set_credentials(username, new_password)