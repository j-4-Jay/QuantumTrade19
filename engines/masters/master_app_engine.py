"""Master App Engine - orchestrates UI Experience Monitor + Security Monitor + Market Data Monitor.

PATH: engines/masters/master_app_engine.py (REPLACE ENTIRE FILE - fully overwrite, don't merge)

CHANGE (Timezone Mode toggle) - added set_poi_timezone_mode(mode) flat
passthrough, same None-guard pattern as every other POI passthrough here.

CHANGE (v0.5.0 - POI Chart Overlay Wiring, carried forward) - added
get_active_pois(symbol) and get_poi_state(symbol, poi_id) flat
passthrough methods.

CHANGE (File 03.1 Scope E, unchanged): added a lazily-started POIMonitor
plus passthrough methods for the Settings card. Deliberately NOT
constructed in __init__ - POIMonitor's constructor immediately probes
historical candles for every active symbol across all 8 timeframes,
which would mean every test that constructs MasterAppEngine(force_memory=True)
would suddenly trigger real network calls. Uses the exact same lazy-start
pattern as ensure_market_data_started() for this reason.

CHANGE (Module 01 gap-closure item 10, unchanged): attempt_login() accepts
remember_device - on successful login, if checked, calls
security.trust_this_device() to persist the 60-day device-trust timestamp.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from engines.monitors.security_monitor import SecurityMonitor
from engines.monitors.ui_experience_monitor import UIExperienceMonitor
from engines.monitors.market_data_monitor import MarketDataMonitor
from engines.monitors.poi_monitor import POIMonitor
from engines.workers.market_data.coindcx_socket_transport import CoinDCXSocketTransport
from engines.event_bus.bus import event_bus
from engines.monitors.setup_detection_monitor import SetupDetectionMonitor

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
        self.poi_monitor: Optional[POIMonitor] = None
        self._poi_monitor_started = False
        self.setup_detection_monitor: Optional[SetupDetectionMonitor] = None
        self._setup_detection_monitor_started = False
        self.screen: ShellScreen = ShellScreen.SPLASH
        self.paper_mode: bool = True

    def ensure_market_data_started(self) -> None:
        """Call this once when the app shell loads. Safe to call many times."""
        if not self._market_data_started:
            self.market_data.start()
            self._market_data_started = True

    def ensure_poi_monitor_started(self) -> None:
        """Call this once when the app shell loads, after market data is
        available. Safe to call many times. Deliberately lazy - see module
        docstring for why this is not constructed in __init__."""
        if not self._poi_monitor_started:
            self.poi_monitor = POIMonitor(self.market_data, self.market_data.symbol_registry)
            self._poi_monitor_started = True
    
    
    def ensure_setup_detection_monitor_started(self) -> None:
        """File 04.1 wiring: lazily builds SetupDetectionMonitor exactly once,
        registers it to receive every closed candle from MarketDataMonitor,
        and depends on POIMonitor already being started (same lazy pattern
        as ensure_poi_monitor_started)."""
        if not self._setup_detection_monitor_started:
            self.ensure_poi_monitor_started()
            self.setup_detection_monitor = SetupDetectionMonitor(
                self.poi_monitor, self.market_data.symbol_registry
            )
            self.market_data.add_candle_close_subscriber(
                self.setup_detection_monitor.on_candle_closed
            )
            self._setup_detection_monitor_started = True

    def get_confirmed_setups(self, symbol: str, tf: str):
        self.ensure_setup_detection_monitor_started()
        return self.setup_detection_monitor.get_confirmed_setups(symbol, tf)

    def get_pending_setups(self, symbol: str, tf: str):
        self.ensure_setup_detection_monitor_started()
        return self.setup_detection_monitor.get_pending_setups(symbol, tf)
        
    
    
    
    

    def get_poi_settings(self) -> dict:
        return self.poi_monitor.get_poi_settings() if self.poi_monitor else {}

    def set_poi_display_enabled(self, poi_type: str, enabled: bool) -> None:
        if self.poi_monitor:
            self.poi_monitor.set_poi_display_enabled(poi_type, enabled)

    def set_poi_strategy_enabled(self, poi_type: str, enabled: bool) -> None:
        if self.poi_monitor:
            self.poi_monitor.set_poi_strategy_enabled(poi_type, enabled)

    def set_poi_zone_source_tf_enabled(self, timeframe: str, enabled: bool) -> None:
        if self.poi_monitor:
            self.poi_monitor.set_zone_source_tf_enabled(timeframe, enabled)

    def set_poi_timezone_mode(self, mode: str) -> None:
        if self.poi_monitor:
            self.poi_monitor.set_poi_timezone_mode(mode)

    def get_active_pois(self, symbol: str) -> list:
        """Flat passthrough to POIMonitor.get_active_pois() - used by
        state/app_state_mixins/poi_chart_mixin.py to render POI lines/zones
        on the Trading Panel chart (File 03.1 Scope C). Returns an empty
        list (never raises) if the POI monitor hasn't been lazily started
        yet - same safety pattern as get_poi_settings() above."""
        return self.poi_monitor.get_active_pois(symbol) if self.poi_monitor else []

    def get_poi_state(self, symbol: str, poi_id: str):
        """Flat passthrough to POIMonitor.get_poi_state() - returns None
        (never raises) if the POI monitor hasn't been lazily started yet."""
        return self.poi_monitor.get_poi_state(symbol, poi_id) if self.poi_monitor else None

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
