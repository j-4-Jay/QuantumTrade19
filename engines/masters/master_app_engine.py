"""Master App Engine - orchestrates UI Experience Monitor + Security Monitor + Market Data Monitor.

PATH: engines/masters/master_app_engine.py (REPLACE ENTIRE FILE - fully overwrite, don't merge)

CHANGE (Module 01 gap-closure item 10): attempt_login() now accepts remember_device - on
successful login, if checked, it calls security.trust_this_device() to persist the 60-day
device-trust timestamp. Also added go_to_register() (bugfix from earlier this session).
"""
from __future__ import annotations
from enum import Enum
from engines.monitors.security_monitor import SecurityMonitor
from engines.monitors.ui_experience_monitor import UIExperienceMonitor
from engines.monitors.market_data_monitor import MarketDataMonitor
from engines.workers.market_data.coindcx_socket_transport import CoinDCXSocketTransport
from engines.event_bus.bus import event_bus

class ShellScreen(str, Enum):
    SPLASH = "splash"
    REGISTER = "register"
    LOGIN = "login"
    MANAGE_SECURITY = "manage_security"
    FORGOT_PASSWORD = "forgot_password"
    SHELL = "shell"
    LOCKED = "locked"

class MasterAppEngine:
    def __init__(self, force_memory: bool = False) -> None:
        self.security = SecurityMonitor(force_memory=force_memory)
        self.ui = UIExperienceMonitor()
        self.market_data = MarketDataMonitor(transport=CoinDCXSocketTransport())
        self._market_data_started = False
        self.screen: ShellScreen = ShellScreen.SPLASH
        self.paper_mode: bool = True

    def ensure_market_data_started(self) -> None:
        """Call this once when the app shell loads. Safe to call many times."""
        if not self._market_data_started:
            self.market_data.start()
            self._market_data_started = True

    def get_market_data_health(self) -> str:
        """Collapses per-symbol health into one value for the topbar dot:
        'connecting' | 'connected' | 'degraded' | 'down'."""
        health = self.market_data.get_health()
        if not health:
            return "connecting"
        values = set(health.values())
        if values == {"OK"}:
            return "connected"
        if "OK" in values or "DEGRADED" in values:
            return "degraded"
        return "down"

    def finish_splash(self) -> ShellScreen:
        self.screen = ShellScreen.REGISTER if self.security.is_first_run() else ShellScreen.LOGIN
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def go_to_login(self) -> ShellScreen:
        self.screen = ShellScreen.LOGIN
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def go_to_register(self) -> ShellScreen:
        self.screen = ShellScreen.REGISTER
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def register_credentials(self, username: str, password: str) -> bool:
        return self.security.register_credentials(username, password)

    def finish_registration_without_totp(self, username: str, password: str) -> bool:
        self.security.disable_totp()
        ok = self.security.login(username, password, None)
        if ok:
            self.screen = ShellScreen.SHELL
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    def finish_registration_with_totp(self, username: str, password: str, code: str) -> bool:
        if not self.security.confirm_totp_enrollment(code):
            return False
        ok = self.security.login(username, password, code)
        if ok:
            self.screen = ShellScreen.SHELL
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    def attempt_login(self, username: str, password: str, totp_code: str | None = None, remember_device: bool = False) -> bool:
        ok = self.security.login(username, password, totp_code)
        if ok:
            if remember_device:
                self.security.trust_this_device()
            self.screen = ShellScreen.SHELL
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    def lock(self) -> None:
        self.security.lock_ui()
        self.screen = ShellScreen.LOCKED
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})

    def unlock(self, password: str, totp_code: str | None = None) -> bool:
        ok = self.security.login(self._current_username(), password, totp_code)
        if ok:
            self.screen = ShellScreen.SHELL
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    def _current_username(self) -> str:
        return self.security.keystore.get_secret("auth_username") or ""

    def toggle_paper_live(self) -> bool:
        self.paper_mode = not self.paper_mode
        self.security.persistence.save({"paper_mode": self.paper_mode})
        event_bus.publish("shell.paper_mode_changed", {"paper_mode": self.paper_mode})
        return self.paper_mode

    # --- Manage Account Security ---
    def begin_manage_security(self) -> ShellScreen:
        self.screen = ShellScreen.MANAGE_SECURITY
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def verify_manage_security_identity(self, username: str, password: str) -> bool:
        return self.security.auth.verify(username, password)

    def manage_totp_begin_enable(self, username: str) -> str:
        return self.security.begin_totp_enrollment(username)

    def manage_totp_confirm_enable(self, code: str) -> bool:
        return self.security.confirm_totp_enrollment(code)

    def manage_totp_disable(self) -> None:
        self.security.disable_totp()

    def manage_save_telegram(self, bot_token: str, chat_id: str, enabled: bool) -> None:
        self.security.set_telegram_config(bot_token, chat_id, enabled)

    def manage_test_telegram(self) -> tuple[bool, str]:
        return self.security.send_test_telegram()

    def manage_is_telegram_configured(self) -> bool:
        return self.security.has_telegram_configured()

    def manage_save_discord(self, webhook_url: str, enabled: bool) -> None:
        self.security.set_discord_config(webhook_url, enabled)

    def manage_test_discord(self) -> tuple[bool, str]:
        return self.security.send_test_discord()

    def manage_is_discord_configured(self) -> bool:
        return self.security.has_discord_configured()

    def finish_manage_security(self) -> ShellScreen:
        self.screen = ShellScreen.LOGIN
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    # --- Forgot Password ---
    def begin_forgot_password(self) -> ShellScreen:
        self.screen = ShellScreen.FORGOT_PASSWORD
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def cancel_forgot_password(self) -> ShellScreen:
        self.screen = ShellScreen.LOGIN
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen

    def has_any_recovery_method(self) -> bool:
        return self.security.has_any_recovery_method()

    def available_reset_methods(self) -> list[str]:
        return self.security.available_reset_methods()

    def send_forgot_otp(self, method: str) -> bool:
        return self.security.send_forgot_otp(method)

    def verify_identity_for_reset(self, method: str, code: str) -> bool:
        return self.security.verify_identity_for_reset(method, code)

    def reset_password(self, new_password: str) -> bool:
        username = self._current_username()
        if not username:
            return False
        ok = self.security.reset_password(username, new_password)
        if ok:
            self.screen = ShellScreen.LOGIN
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    def reset_password_unverified(self, new_password: str) -> bool:
        username = self._current_username()
        if not username:
            return False
        ok = self.security.reset_password(username, new_password)
        if ok:
            self.screen = ShellScreen.LOGIN
            event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return ok

    # --- Logout ---
    def has_open_trades(self) -> bool:
        return False

    def logout(self, close_trades: bool | None) -> ShellScreen:
        self.security.app_lock.unlock()
        self.screen = ShellScreen.SPLASH
        event_bus.publish("shell.logout", {"close_trades": close_trades})
        event_bus.publish("shell.screen_changed", {"screen": self.screen.value})
        return self.screen