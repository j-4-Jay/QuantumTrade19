"""Reflex State - thin UI binding layer over the Master App Engine (no business logic here).

PATH: state/app_state.py  (REPLACE ENTIRE FILE)

FIX (checkbox/toggle lag - same root cause as the page-load freeze, different
trigger): every POIMonitor setting-change method (set_poi_display_enabled,
set_poi_strategy_enabled, set_zone_source_tf_enabled) doesn't just flip a
flag - it calls _recompute_symbol() for every active symbol, which makes
real blocking network calls to CoinDCX across all five Worker types. Since
toggle_poi_display/toggle_poi_strategy/toggle_poi_zone_source_tf were still
plain (non-background) event handlers, every checkbox click froze the
shared asyncio event loop exactly like the original page-load issue did.

Fixed by converting these three handlers, plus all four bulk-control
methods (which loop this same expensive call across many POI types), into
real background events. Each now updates the UI-facing state dict
immediately (so the checkbox visually flips right away) before offloading
the actual slow engine call to a separate OS thread via asyncio.to_thread().
The backend settings change and recompute still take a few real seconds to
finish (that's genuine network I/O, not a bug), but the UI itself no longer
freezes while waiting.

FIX (severe app-wide lag on page load, from previous round, unchanged):
POI monitor startup already runs via start_poi_monitor_background using
asyncio.to_thread() instead of blocking on_load() directly.

CHANGE (File 03.1 Scope E, otherwise unchanged): POI Engine & Chart
Visibility settings state, computed vars, and event handlers for the
Settings card. Visual-only POI preferences persist through the existing
SettingsPersistenceWorker under a new "poi_visual_settings" key.

CHANGE (Module 01 gap-closure item 10): added login_remember_device / toggle_login_remember_device
for the "Remember this device (skip 2FA for 60 days)" checkbox on Login. submit_login() now
passes that flag through to MasterAppEngine.attempt_login() and resets it on success.
run_splash_sequence() now also checks security.is_device_trusted() so the TOTP field correctly
stays hidden on subsequent logins from an already-trusted device.

CHANGE (Module 01 gap-closure item 8, Settings-controlled tab animation): added
tab_transition_effects_enabled / tab_transition_mode / tab_transition_active_effect /
_tab_transition_sequence_index, loaded in on_load, driven by a new _pick_tab_transition_effect
(mirrors _pick_transition_effect but routes through the same PageTransitionWorker.pick() with
an independent pool/mode), plus toggle_tab_transition_effect / set_tab_transition_mode for the
new Settings card, and set_active_tab now picks a fresh tab effect + plays the tab-slide sound
on every switch.

FIX (the recurring post-splash delay): browser console confirmed React Strict Mode is active
in this dev build, which deliberately double-invokes mount effects (mount -> cleanup -> mount
again) to catch missing cleanup logic. Reflex's `on_mount` almost certainly runs through this
same mechanism, meaning `run_splash_sequence` was very likely starting TWICE on every splash
mount - the first copy finishes and correctly flips the screen to Login, but the SECOND,
duplicate copy keeps running in the same per-session event queue, and any click has to wait
behind it until it finishes. Added `_splash_task_running` as a guard: the second, duplicate
invocation now exits immediately instead of re-running the whole 5s+2s wait a second time.
"""
from __future__ import annotations
import asyncio
import random
import reflex as rx
from engines.masters.master_app_engine import MasterAppEngine, ShellScreen
PINNED_SYMBOL_MAP = {
        "BTCUSD": "B-BTC_USDT",
        "ETHUSD": "B-ETH_USDT",
        "Gold": "B-XAU_USDT",  # not yet in Symbol_Registry_Worker - will show "--" until added
    }


POI_LINE_TF_ORDER = ["1m", "5m", "15m", "1H", "4H", "1D", "1W", "1M"]
POI_LINE_TF_LABELS = {
    "1m": "1 Minute", "5m": "5 Minute", "15m": "15 Minute", "1H": "1 Hour",
    "4H": "4 Hour", "1D": "Daily", "1W": "Weekly", "1M": "Monthly",
}
POI_LINE_TYPE_MAP = {
    "1m": ("P1M_HIGH", "P1M_LOW"), "5m": ("P5M_HIGH", "P5M_LOW"), "15m": ("P15M_HIGH", "P15M_LOW"),
    "1H": ("P1H_HIGH", "P1H_LOW"), "4H": ("4H_HIGH", "4H_LOW"), "1D": ("PDH", "PDL"),
    "1W": ("1W_HIGH", "1W_LOW"), "1M": ("1M_HIGH", "1M_LOW"),
}
POI_ZONE_TYPES = [
    ("RESISTANCE_FLIP", "Resistance Flip"), ("SUPPORT_FLIP", "Support Flip"),
    ("FVG", "Fair Value Gap"), ("INVERSE_FVG", "Inverse FVG"), ("ORDER_BLOCK", "Order Block"),
]
POI_DEFAULT_STRATEGY_TYPES = {"4H_HIGH", "4H_LOW", "PDH", "PDL"}




from config.settings import (
    THEMES, DEFAULT_THEME_KEY, SIDEBAR_TABS, THEME_ORDER, THEME_LABELS,
    SPLASH_DURATION_SECONDS, SPLASH_HOLD_SECONDS, TRANSITION_EFFECTS,
)



_engine = MasterAppEngine()




class AppState(rx.State):
    screen: str = ShellScreen.SPLASH.value
    active_tab: str = "Dashboard"
    theme_key: str = DEFAULT_THEME_KEY
    paper_mode: bool = True
    is_locked: bool = False
    sound_muted: bool = False



    totp_required: bool = False



    reg_username: str = ""
    reg_password: str = ""
    reg_confirm_password: str = ""
    reg_enable_totp: bool = False
    reg_error: str = ""
    reg_stage: str = "form"
    reg_qr_data_uri: str = ""
    reg_totp_code: str = ""
    show_reg_password: bool = False
    show_reg_confirm_password: bool = False



    login_username: str = ""
    login_password: str = ""
    login_totp: str = ""
    login_error: str = ""
    show_login_password: bool = False
    show_lock_password: bool = False
    login_credentials_match: bool = False
    login_error_seq: int = 0
    login_remember_device: bool = False



    manage_username: str = ""
    manage_password: str = ""
    manage_error: str = ""
    manage_stage: str = "verify"
    manage_totp_qr: str = ""
    manage_totp_code: str = ""
    show_manage_password: bool = False
    tg_bot_token: str = ""
    tg_chat_id: str = ""
    tg_enabled: bool = False
    tg_configured: bool = False
    tg_message: str = ""
    dc_webhook_url: str = ""
    dc_enabled: bool = False
    dc_configured: bool = False
    dc_message: str = ""



    forgot_stage: str = "choose"
    forgot_selected_method: str = ""
    forgot_code: str = ""
    forgot_otp_sent: bool = False
    forgot_verified: bool = False
    forgot_new_password: str = ""
    forgot_confirm_password: str = ""
    forgot_error: str = ""
    show_forgot_new_password: bool = False
    show_forgot_confirm_password: bool = False
    forgot_available_methods: list[str] = []
    forgot_has_any_method: bool = False



    show_logout_dialog: bool = False
    logout_stage: str = "confirm"



    detail_popup_open: bool = False
    detail_popup_symbol: str = ""
    ws_status: str = "connected"
    pinned_prices: dict[str, str] = {}
    symbol_rows: list[dict] = []
    deep_history_symbol: str = "B-BTC_USDT"
    deep_history_timeframe: str = "1m"
    deep_history_target_days: str = ""
    deep_history_ceiling_days: str = "Not checked yet"
    deep_history_covered_days: str = "0"
    deep_history_is_downloading: bool = False
    deep_history_status_message: str = ""



    poi_settings_loaded: bool = False
    poi_display_enabled: dict[str, bool] = {}
    poi_strategy_enabled: dict[str, bool] = {}
    poi_zone_source_tf_enabled: dict[str, bool] = {}
    poi_show_labels: bool = True
    poi_show_tooltips: bool = True
    poi_line_transparency: int = 100
    poi_zone_opacity: int = 30
    poi_show_source_tf_badge: bool = True
    poi_show_logical_id: bool = False
    poi_reduced_motion: bool = False
    poi_backend_busy: bool = False



    transition_effects_enabled: list[str] = ["dissolve", "zoom-in", "slide-up", "flip-x", "blur-in"]
    transition_mode: str = "shuffle"
    transition_active_effect: str = "dissolve"
    _transition_sequence_index: int = 0


    tab_transition_effects_enabled: list[str] = ["slide-left"]
    tab_transition_mode: str = "single"
    tab_transition_active_effect: str = "slide-left"
    _tab_transition_sequence_index: int = 0


    _splash_task_running: bool = False
    _ws_poll_running: bool = False
    _price_poll_running: bool = False
    _deep_history_poll_running: bool = False
    _poi_monitor_starting: bool = False



    def on_load(self) -> None:
        self.theme_key = _engine.ui.theme.get_active_key()
        self.paper_mode = _engine.paper_mode
        self.sound_muted = not _engine.ui.sound.is_master_on()
        settings = _engine.security.persistence.load()
        self.transition_effects_enabled = settings.get("transition_effects_enabled", self.transition_effects_enabled)
        self.transition_mode = settings.get("transition_mode", self.transition_mode)
        self.tab_transition_effects_enabled = settings.get("tab_transition_effects_enabled", self.tab_transition_effects_enabled)
        self.tab_transition_mode = settings.get("tab_transition_mode", self.tab_transition_mode)
        _engine.ensure_market_data_started()
        self.refresh_symbol_rows()
        return AppState.start_poi_monitor_background



    @rx.event(background=True)
    async def start_poi_monitor_background(self):
        """POIMonitor's construction makes many blocking network calls
        (every active symbol x every POI Worker type x up to 8 timeframes).
        Running it via asyncio.to_thread() offloads that blocking work to a
        separate OS thread so it never freezes the shared asyncio event
        loop the rest of the app depends on."""
        async with self:
            if self._poi_monitor_starting:
                return
            self._poi_monitor_starting = True
        try:
            await asyncio.to_thread(_engine.ensure_poi_monitor_started)
            async with self:
                self.load_poi_settings()
        finally:
            async with self:
                self._poi_monitor_starting = False



    async def run_splash_sequence(self):
        """Fires the bar-fill animation fresh via rx.call_script, waits the fill duration,
        holds at 100%, then dissolves to Register/Login (hardcoded, never the random pool).
        Guarded against React Strict Mode's double-invocation of on_mount - see module docstring.
        """
        if self._splash_task_running:
            return
        self._splash_task_running = True
        try:
            duration_ms = int(SPLASH_DURATION_SECONDS * 1000)
            yield rx.call_script(
                f"""
                (function() {{
                    const fill = document.getElementById('qt19-splash-bar-fill');
                    const pct = document.getElementById('qt19-splash-pct');
                    if (fill) {{
                        fill.style.transition = 'none';
                        fill.style.transform = 'scaleX(0)';
                        void fill.offsetWidth;
                        fill.style.transition = 'transform {SPLASH_DURATION_SECONDS}s linear';
                        requestAnimationFrame(function() {{ fill.style.transform = 'scaleX(1)'; }});
                    }}
                    if (pct) {{ pct.textContent = '0%'; }}
                    const start = Date.now();
                    const durationMs = {duration_ms};
                    const interval = setInterval(function() {{
                        const elapsed = Date.now() - start;
                        const percent = Math.min(100, Math.round((elapsed / durationMs) * 100));
                        if (pct) {{ pct.textContent = percent + '%'; }}
                        if (elapsed >= durationMs) {{ clearInterval(interval); }}
                    }}, 100);
                }})();
                """
            )
            await asyncio.sleep(SPLASH_DURATION_SECONDS)
            await asyncio.sleep(SPLASH_HOLD_SECONDS)
            self.totp_required = _engine.security.is_totp_enabled() and not _engine.security.is_device_trusted()
            self.transition_active_effect = "dissolve"
            self.screen = _engine.finish_splash().value
        finally:
            self._splash_task_running = False



    def set_reg_username(self, value: str) -> None:
        self.reg_username = value



    def set_reg_password(self, value: str) -> None:
        self.reg_password = value



    def set_reg_confirm_password(self, value: str) -> None:
        self.reg_confirm_password = value



    def set_reg_totp_code(self, value: str) -> None:
        self.reg_totp_code = value



    def toggle_reg_enable_totp(self, checked: bool) -> None:
        self.reg_enable_totp = checked



    def toggle_show_reg_password(self) -> None:
        self.show_reg_password = not self.show_reg_password



    def toggle_show_reg_confirm_password(self) -> None:
        self.show_reg_confirm_password = not self.show_reg_confirm_password



    def _pick_transition_effect(self) -> None:
        effect, next_index = _engine.ui.transitions.pick(
            self.transition_effects_enabled, self.transition_mode, self._transition_sequence_index
        )
        self.transition_active_effect = effect
        self._transition_sequence_index = next_index



    def _pick_tab_transition_effect(self) -> None:
        effect, next_index = _engine.ui.transitions.pick(
            self.tab_transition_effects_enabled, self.tab_transition_mode, self._tab_transition_sequence_index
        )
        self.tab_transition_active_effect = effect
        self._tab_transition_sequence_index = next_index



    def submit_registration(self) -> None:
        if not self.reg_username.strip():
            self.reg_error = "Username is required."
            return
        if len(self.reg_password) < 4:
            self.reg_error = "Password must be at least 4 characters."
            return
        if self.reg_password != self.reg_confirm_password:
            self.reg_error = "Passwords do not match."
            return
        if not _engine.register_credentials(self.reg_username, self.reg_password):
            self.reg_error = "Registration failed. Check your username/password and try again."
            return
        self.reg_error = ""
        if self.reg_enable_totp:
            self.reg_qr_data_uri = _engine.security.begin_totp_enrollment(self.reg_username)
            self.reg_stage = "qr"
        else:
            if _engine.finish_registration_without_totp(self.reg_username, self.reg_password):
                self.totp_required = False
                self._pick_transition_effect()
                self.screen = _engine.screen.value



    def confirm_totp_setup(self) -> None:
        if not self.reg_totp_code.strip():
            self.reg_error = "Enter the 6-digit code from your authenticator app."
            return
        if _engine.finish_registration_with_totp(self.reg_username, self.reg_password, self.reg_totp_code):
            self.reg_error = ""
            self.totp_required = True
            self._pick_transition_effect()
            self.screen = _engine.screen.value
        else:
            self.reg_error = "Incorrect code. Please check your authenticator app and try again."



    def skip_totp_setup(self) -> None:
        self.reg_enable_totp = False
        if _engine.finish_registration_without_totp(self.reg_username, self.reg_password):
            self.totp_required = False
            self._pick_transition_effect()
            self.screen = _engine.screen.value



    def go_to_login(self) -> None:
        self._pick_transition_effect()
        self.screen = _engine.go_to_login().value



    def go_to_register(self) -> None:
        self.reg_username = ""
        self.reg_password = ""
        self.reg_confirm_password = ""
        self.reg_enable_totp = False
        self.reg_error = ""
        self.reg_stage = "form"
        self.reg_qr_data_uri = ""
        self.reg_totp_code = ""
        self._pick_transition_effect()
        self.screen = _engine.go_to_register().value



    def set_login_username(self, value: str) -> None:
        self.login_username = value
        self.login_credentials_match = _engine.security.auth.verify(self.login_username, self.login_password)



    def set_login_password(self, value: str) -> None:
        self.login_password = value
        self.login_credentials_match = _engine.security.auth.verify(self.login_username, self.login_password)



    def set_login_totp(self, value: str) -> None:
        self.login_totp = value



    def toggle_show_login_password(self) -> None:
        self.show_login_password = not self.show_login_password



    def toggle_show_lock_password(self) -> None:
        self.show_lock_password = not self.show_lock_password



    def toggle_login_remember_device(self, checked: bool) -> None:
        self.login_remember_device = checked



    def submit_login(self) -> None:
        if not self.login_username.strip() or len(self.login_password) < 4:
            self.login_error = "Enter your username and password."
            self.login_error_seq += 1
            return self.play_sound("error")
        ok = _engine.attempt_login(self.login_username, self.login_password, self.login_totp or None, self.login_remember_device)
        if ok:
            self.login_error = ""
            self.login_password = ""
            self.login_totp = ""
            self.login_remember_device = False
            self.login_credentials_match = False
            self._pick_transition_effect()
            self.screen = _engine.screen.value
        else:
            self.login_error = "Invalid credentials or authenticator code."
            self.login_error_seq += 1
            return self.play_sound("error")



    def lock_app(self) -> None:
        _engine.lock()
        self._pick_transition_effect()
        self.screen = _engine.screen.value
        self.is_locked = True



    def unlock_app(self) -> None:
        if len(self.login_password) < 4:
            self.login_error = "Password must be at least 4 characters."
            return
        ok = _engine.unlock(self.login_password, self.login_totp or None)
        if ok:
            self.login_error = ""
            self.login_password = ""
            self.login_totp = ""
            self._pick_transition_effect()
            self.screen = _engine.screen.value
            self.is_locked = False
        else:
            self.login_error = "Invalid credentials or authenticator code."



    def begin_manage_security(self) -> None:
        self.manage_username = ""
        self.manage_password = ""
        self.manage_error = ""
        self.manage_stage = "verify"
        self.manage_totp_qr = ""
        self.manage_totp_code = ""
        self.tg_bot_token = ""
        self.tg_chat_id = ""
        self.tg_enabled = _engine.security.is_telegram_enabled()
        self.tg_configured = _engine.manage_is_telegram_configured()
        self.tg_message = ""
        self.dc_webhook_url = ""
        self.dc_enabled = _engine.security.is_discord_enabled()
        self.dc_configured = _engine.manage_is_discord_configured()
        self.dc_message = ""
        self.totp_required = _engine.security.is_totp_enabled()
        self._pick_transition_effect()
        self.screen = _engine.begin_manage_security().value



    def set_manage_username(self, value: str) -> None:
        self.manage_username = value



    def set_manage_password(self, value: str) -> None:
        self.manage_password = value



    def toggle_show_manage_password(self) -> None:
        self.show_manage_password = not self.show_manage_password



    def verify_manage_identity(self) -> None:
        if _engine.verify_manage_security_identity(self.manage_username, self.manage_password):
            self.manage_error = ""
            self.manage_stage = "panel"
            self.totp_required = _engine.security.is_totp_enabled()
        else:
            self.manage_error = "Incorrect username or password."



    def start_enable_totp(self) -> None:
        self.manage_totp_qr = _engine.manage_totp_begin_enable(self.manage_username)
        self.manage_stage = "totp_qr"



    def set_manage_totp_code(self, value: str) -> None:
        self.manage_totp_code = value



    def confirm_enable_totp(self) -> None:
        if not self.manage_totp_code.strip():
            self.manage_error = "Enter the 6-digit code from your authenticator app."
            return
        if _engine.manage_totp_confirm_enable(self.manage_totp_code):
            self.manage_error = ""
            self.manage_stage = "panel"
            self.totp_required = True
        else:
            self.manage_error = "Incorrect code. Please try again."



    def disable_totp(self) -> None:
        _engine.manage_totp_disable()
        self.totp_required = False



    def set_tg_bot_token(self, value: str) -> None:
        self.tg_bot_token = value



    def set_tg_chat_id(self, value: str) -> None:
        self.tg_chat_id = value



    def toggle_tg_enabled(self, checked: bool) -> None:
        self.tg_enabled = checked



    def save_telegram(self) -> None:
        _engine.manage_save_telegram(self.tg_bot_token, self.tg_chat_id, self.tg_enabled)
        self.tg_configured = _engine.manage_is_telegram_configured()
        self.tg_bot_token = ""
        self.tg_message = "Saved." if self.tg_configured else "Saved, but no bot token/chat ID is on file yet - enter both once."



    def test_telegram(self) -> None:
        success, detail = _engine.manage_test_telegram()
        self.tg_message = detail



    def set_dc_webhook_url(self, value: str) -> None:
        self.dc_webhook_url = value



    def toggle_dc_enabled(self, checked: bool) -> None:
        self.dc_enabled = checked



    def save_discord(self) -> None:
        _engine.manage_save_discord(self.dc_webhook_url, self.dc_enabled)
        self.dc_configured = _engine.manage_is_discord_configured()
        self.dc_webhook_url = ""
        self.dc_message = "Saved." if self.dc_configured else "Saved, but no webhook URL is on file yet - enter one once."



    def test_discord(self) -> None:
        success, detail = _engine.manage_test_discord()
        self.dc_message = detail



    def finish_manage_security(self) -> None:
        self._pick_transition_effect()
        self.screen = _engine.finish_manage_security().value



    def begin_forgot_password(self) -> None:
        self.forgot_selected_method = ""
        self.forgot_code = ""
        self.forgot_otp_sent = False
        self.forgot_verified = False
        self.forgot_new_password = ""
        self.forgot_confirm_password = ""
        self.forgot_error = ""
        self.forgot_has_any_method = _engine.has_any_recovery_method()
        self.forgot_available_methods = _engine.available_reset_methods()
        self.forgot_stage = "reset" if not self.forgot_has_any_method else "choose"
        self._pick_transition_effect()
        self.screen = _engine.begin_forgot_password().value



    def cancel_forgot_password(self) -> None:
        self.forgot_new_password = ""
        self.forgot_confirm_password = ""
        self.forgot_error = ""
        self._pick_transition_effect()
        self.screen = _engine.cancel_forgot_password().value



    def select_forgot_method(self, method: str) -> None:
        self.forgot_selected_method = method
        self.forgot_error = ""
        if method == "totp":
            self.forgot_stage = "enter_code"
        else:
            if _engine.send_forgot_otp(method):
                self.forgot_otp_sent = True
                self.forgot_stage = "enter_code"
            else:
                self.forgot_error = f"Could not send a code via {method.title()}. Check the channel configuration in Manage Account Security."



    def resend_forgot_otp(self) -> None:
        if self.forgot_selected_method in ("telegram", "discord"):
            _engine.send_forgot_otp(self.forgot_selected_method)
            self.forgot_otp_sent = True



    def set_forgot_code(self, value: str) -> None:
        self.forgot_code = value



    def verify_forgot_identity(self) -> None:
        if not self.forgot_code.strip():
            self.forgot_error = "Enter the code."
            return
        if _engine.verify_identity_for_reset(self.forgot_selected_method, self.forgot_code):
            self.forgot_error = ""
            self.forgot_verified = True
            self.forgot_stage = "reset"
        else:
            self.forgot_error = "That code did not match. Double-check and try again."



    def set_forgot_new_password(self, value: str) -> None:
        self.forgot_new_password = value



    def set_forgot_confirm_password(self, value: str) -> None:
        self.forgot_confirm_password = value



    def toggle_show_forgot_new_password(self) -> None:
        self.show_forgot_new_password = not self.show_forgot_new_password



    def toggle_show_forgot_confirm_password(self) -> None:
        self.show_forgot_confirm_password = not self.show_forgot_confirm_password



    def submit_new_password(self) -> None:
        if len(self.forgot_new_password) < 4:
            self.forgot_error = "Password must be at least 4 characters."
            return
        if self.forgot_new_password != self.forgot_confirm_password:
            self.forgot_error = "Passwords do not match."
            return
        if self.forgot_verified:
            ok = _engine.reset_password(self.forgot_new_password)
        else:
            ok = _engine.reset_password_unverified(self.forgot_new_password)
        if ok:
            self.forgot_error = ""
            self._pick_transition_effect()
            self.screen = _engine.screen.value
        else:
            self.forgot_error = "Could not reset password. Please try again."



    def open_logout_dialog(self) -> None:
        self.logout_stage = "trade_choice" if _engine.has_open_trades() else "confirm"
        self.show_logout_dialog = True



    def close_logout_dialog(self) -> None:
        self.show_logout_dialog = False



    def _do_logout(self, close_trades: bool | None) -> None:
        self._pick_transition_effect()
        self.screen = _engine.logout(close_trades).value
        self.show_logout_dialog = False
        self.login_username = ""
        self.login_password = ""
        self.login_totp = ""
        self.login_error = ""
        self.login_credentials_match = False



    def confirm_logout_no_trades(self) -> None:
        self._do_logout(None)



    def confirm_logout_close_trades(self) -> None:
        self._do_logout(True)



    def confirm_logout_keep_trades(self) -> None:
        self._do_logout(False)



    def set_active_tab(self, tab: str) -> None:
        self.active_tab = tab
        self.detail_popup_open = False
        self._pick_tab_transition_effect()
        return self.play_sound("tab-slide")



    def set_theme(self, key: str) -> None:
        if _engine.ui.theme.set_active_key(key):
            self.theme_key = key



    def toggle_sound(self) -> None:
        is_on = _engine.ui.sound.toggle_master()
        self.sound_muted = not is_on



    def play_sound(self, event_name: str):
        url = _engine.ui.play_sound(event_name)
        if not url:
            return
        return rx.call_script(
            f"(function(){{ try {{ new Audio('{url}').play().catch(function(){{}}); }} "
            f"catch(e) {{}} }})();"
        )



    @rx.event(background=True)
    async def poll_ws_status(self):
        async with self:
            if self._ws_poll_running:
                return
            self._ws_poll_running = True
        try:
            while True:
                async with self:
                    self.ws_status = _engine.get_market_data_health()
                await asyncio.sleep(3)
        finally:
            async with self:
                self._ws_poll_running = False




    @rx.event(background=True)
    async def poll_pinned_prices(self):
        async with self:
            if getattr(self, "_price_poll_running", False):
                return
            self._price_poll_running = True
        try:
            while True:
                snapshot = {}
                for display_name, real_symbol in PINNED_SYMBOL_MAP.items():
                    candle = _engine.market_data.get_live_candle(real_symbol, "1m")
                    if candle:
                        snapshot[display_name] = f"{candle.close:,.2f}"
                    else:
                        snapshot[display_name] = "--"
                async with self:
                    self.pinned_prices = snapshot
                await asyncio.sleep(2)
        finally:
            async with self:
                self._price_poll_running = False



    def toggle_paper_live(self) -> None:
        self.paper_mode = _engine.toggle_paper_live()


    def refresh_symbol_rows(self) -> None:
        """Rebuilds the Dashboard table's row list: favorites first
        (alphabetical), then everything else (alphabetical)."""
        registry = _engine.market_data.symbol_registry
        ordered_symbols = registry.get_symbols_sorted(active_only=True)
        rows = []
        for symbol in ordered_symbols:
            info = registry.get_symbol_info(symbol)
            rows.append({
                "symbol": symbol,
                "is_favorite": info.is_favorite if info else False,
            })
        self.symbol_rows = rows



        
    def toggle_favorite(self, symbol: str) -> None:
        registry = _engine.market_data.symbol_registry
        info = registry.get_symbol_info(symbol)
        if info is None:
            return
        registry.set_favorite(symbol, not info.is_favorite)
        self.refresh_symbol_rows()




    def set_deep_history_symbol(self, value: str) -> None:
        self.deep_history_symbol = value
        self.refresh_deep_history_status()


    def set_deep_history_timeframe(self, value: str) -> None:
        self.deep_history_timeframe = value
        self.refresh_deep_history_status()


    def set_deep_history_target_days(self, value: str) -> None:
        self.deep_history_target_days = value


    def check_deep_history_ceiling(self):
        self.deep_history_status_message = "Checking real ceiling... this can take a few minutes for 1m/5m."
        _engine.market_data.start_ceiling_probe(self.deep_history_symbol, self.deep_history_timeframe)
        return AppState.poll_deep_history_status


    def refresh_deep_history_status(self) -> None:
        progress = _engine.market_data.get_deep_history_progress(
            self.deep_history_symbol, self.deep_history_timeframe
        )
        self.deep_history_covered_days = str(progress["covered_days"])
        ceiling = _engine.market_data.get_ceiling_days(self.deep_history_symbol, self.deep_history_timeframe)
        self.deep_history_ceiling_days = f"{ceiling} days" if ceiling is not None else "Not checked yet"


    def start_deep_history_download(self):
        try:
            target = int(self.deep_history_target_days) if self.deep_history_target_days.strip() else None
        except ValueError:
            self.deep_history_status_message = "Enter a valid whole number of days, or leave blank for 'download all'."
            return
        self.deep_history_is_downloading = True
        self.deep_history_status_message = "Download started..."
        _engine.market_data.start_deep_history(self.deep_history_symbol, self.deep_history_timeframe, target)
        return AppState.poll_deep_history_status


    def cancel_deep_history_download(self) -> None:
        _engine.market_data.cancel_deep_history(self.deep_history_symbol, self.deep_history_timeframe)
        self.deep_history_is_downloading = False
        self.deep_history_status_message = "Cancelled."


    def delete_deep_history_data(self) -> None:
        _engine.market_data.delete_deep_history(self.deep_history_symbol, self.deep_history_timeframe)
        self.deep_history_status_message = "Deep archive deleted for this symbol (all its timeframes). 5-day baseline is untouched."
        self.refresh_deep_history_status()


    @rx.event(background=True)
    async def poll_deep_history_status(self):
        async with self:
            if self._deep_history_poll_running:
                return
            self._deep_history_poll_running = True
        try:
            still_active = True
            while still_active:
                async with self:
                    self.refresh_deep_history_status()
                    still_active = (
                        _engine.market_data.deep_history_downloader.is_downloading(
                            self.deep_history_symbol, self.deep_history_timeframe
                        )
                        or _engine.market_data.depth_prober.is_probing(
                            self.deep_history_symbol, self.deep_history_timeframe
                        )
                    )
                    if not still_active:
                        self.deep_history_is_downloading = False
                        if self.deep_history_status_message == "Download started...":
                            self.deep_history_status_message = "Download complete or paused (target reached)."
                await asyncio.sleep(3)
        finally:
            async with self:
                self._deep_history_poll_running = False



    def load_poi_settings(self) -> None:
        settings = _engine.get_poi_settings()
        self.poi_display_enabled = settings.get("display_enabled", {})
        self.poi_strategy_enabled = settings.get("strategy_enabled", {})
        self.poi_zone_source_tf_enabled = settings.get("zone_source_tf_enabled", {})
        visual = _engine.security.persistence.load().get("poi_visual_settings", {})
        self.poi_show_labels = visual.get("show_labels", True)
        self.poi_show_tooltips = visual.get("show_tooltips", True)
        self.poi_line_transparency = visual.get("line_transparency", 100)
        self.poi_zone_opacity = visual.get("zone_opacity", 30)
        self.poi_show_source_tf_badge = visual.get("show_source_tf_badge", True)
        self.poi_show_logical_id = visual.get("show_logical_id", False)
        self.poi_reduced_motion = visual.get("reduced_motion", False)
        self.poi_settings_loaded = True


    @rx.event(background=True)
    async def toggle_poi_display(self, poi_type: str, checked: bool):
        """Updates the checkbox immediately, then offloads the real,
        network-bound recompute POIMonitor triggers internally to a
        separate thread so it never freezes the UI."""
        async with self:
            self.poi_display_enabled = {**self.poi_display_enabled, poi_type: checked}
            self.poi_backend_busy = True
        try:
            await asyncio.to_thread(_engine.set_poi_display_enabled, poi_type, checked)
        finally:
            async with self:
                self.poi_backend_busy = False


    @rx.event(background=True)
    async def toggle_poi_strategy(self, poi_type: str, checked: bool):
        async with self:
            self.poi_strategy_enabled = {**self.poi_strategy_enabled, poi_type: checked}
            self.poi_backend_busy = True
        try:
            await asyncio.to_thread(_engine.set_poi_strategy_enabled, poi_type, checked)
        finally:
            async with self:
                self.poi_backend_busy = False


    @rx.event(background=True)
    async def toggle_poi_zone_source_tf(self, timeframe: str, checked: bool):
        async with self:
            self.poi_zone_source_tf_enabled = {**self.poi_zone_source_tf_enabled, timeframe: checked}
            self.poi_backend_busy = True
        try:
            await asyncio.to_thread(_engine.set_poi_zone_source_tf_enabled, timeframe, checked)
        finally:
            async with self:
                self.poi_backend_busy = False


    def _save_poi_visual_settings(self) -> None:
        _engine.security.persistence.save({"poi_visual_settings": {
            "show_labels": self.poi_show_labels,
            "show_tooltips": self.poi_show_tooltips,
            "line_transparency": self.poi_line_transparency,
            "zone_opacity": self.poi_zone_opacity,
            "show_source_tf_badge": self.poi_show_source_tf_badge,
            "show_logical_id": self.poi_show_logical_id,
            "reduced_motion": self.poi_reduced_motion,
        }})


    def toggle_poi_show_labels(self, checked: bool) -> None:
        self.poi_show_labels = checked
        self._save_poi_visual_settings()


    def toggle_poi_show_tooltips(self, checked: bool) -> None:
        self.poi_show_tooltips = checked
        self._save_poi_visual_settings()


    def toggle_poi_show_source_tf_badge(self, checked: bool) -> None:
        self.poi_show_source_tf_badge = checked
        self._save_poi_visual_settings()


    def toggle_poi_show_logical_id(self, checked: bool) -> None:
        self.poi_show_logical_id = checked
        self._save_poi_visual_settings()


    def toggle_poi_reduced_motion(self, checked: bool) -> None:
        self.poi_reduced_motion = checked
        self._save_poi_visual_settings()


    def set_poi_line_transparency(self, value: list[float]) -> None:
        self.poi_line_transparency = int(value[0])
        self._save_poi_visual_settings()


    def set_poi_zone_opacity(self, value: list[float]) -> None:
        self.poi_zone_opacity = int(value[0])
        self._save_poi_visual_settings()


    @rx.event(background=True)
    async def poi_show_all(self):
        async with self:
            poi_types = list(self.poi_display_enabled.keys())
            self.poi_display_enabled = {t: True for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_display_enabled(t, True)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False


    @rx.event(background=True)
    async def poi_hide_all(self):
        async with self:
            poi_types = list(self.poi_display_enabled.keys())
            self.poi_display_enabled = {t: False for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_display_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False


    @rx.event(background=True)
    async def poi_enable_default_strategy(self):
        async with self:
            poi_types = list(self.poi_strategy_enabled.keys())
            self.poi_strategy_enabled = {t: (t in POI_DEFAULT_STRATEGY_TYPES) for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_strategy_enabled(t, t in POI_DEFAULT_STRATEGY_TYPES)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False


    @rx.event(background=True)
    async def poi_disable_all_strategy(self):
        async with self:
            poi_types = list(self.poi_strategy_enabled.keys())
            self.poi_strategy_enabled = {t: False for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_strategy_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False


    def poi_reset_chart_filters(self) -> None:
        """Temporary chart filters are session-only per spec and never
        persisted - this is a placeholder no-op until Scope C's chart exists
        to actually hold them."""
        pass



    def open_detail_popup(self, symbol: str) -> None:
        self.detail_popup_symbol = symbol
        self.detail_popup_open = True



    def close_detail_popup(self) -> None:
        self.detail_popup_open = False



    def toggle_transition_effect(self, effect: str, checked: bool) -> None:
        current = list(self.transition_effects_enabled)
        if checked and effect not in current:
            current.append(effect)
        elif not checked and effect in current:
            current.remove(effect)
        if not current:
            current = [effect]
        self.transition_effects_enabled = current
        _engine.security.persistence.save({"transition_effects_enabled": current})



    def set_transition_mode(self, mode: str) -> None:
        self.transition_mode = mode
        _engine.security.persistence.save({"transition_mode": mode})



    def toggle_tab_transition_effect(self, effect: str, checked: bool) -> None:
        current = list(self.tab_transition_effects_enabled)
        if checked and effect not in current:
            current.append(effect)
        elif not checked and effect in current:
            current.remove(effect)
        if not current:
            current = [effect]
        self.tab_transition_effects_enabled = current
        _engine.security.persistence.save({"tab_transition_effects_enabled": current})



    def set_tab_transition_mode(self, mode: str) -> None:
        self.tab_transition_mode = mode
        _engine.security.persistence.save({"tab_transition_mode": mode})



    @rx.var
    def theme_vars(self) -> dict[str, str]:
        t = THEMES[self.theme_key]
        return {
            "accent": t.accent, "accent_glow": t.accent_glow, "bg_from": t.bg_from, "bg_to": t.bg_to,
            "glass_bg": t.glass_bg, "glass_border": t.glass_border,
            "text_primary": t.text_primary, "text_muted": t.text_muted,
        }



    @rx.var
    def sidebar_tabs(self) -> list[str]:
        return SIDEBAR_TABS



    @rx.var
    def theme_options(self) -> list[dict[str, str]]:
        return [{"key": k, "label": THEME_LABELS[k]} for k in THEME_ORDER]



    @rx.var
    def transition_effect_options(self) -> list[dict[str, str]]:
        return [{"key": k, "label": v} for k, v in TRANSITION_EFFECTS.items()]



    @rx.var
    def poi_line_rows(self) -> list[dict]:
        rows = []
        for tf in POI_LINE_TF_ORDER:
            high_type, low_type = POI_LINE_TYPE_MAP[tf]
            rows.append({
                "tf": tf, "label": POI_LINE_TF_LABELS[tf],
                "high_type": high_type, "low_type": low_type,
                "high_display": self.poi_display_enabled.get(high_type, False),
                "high_strategy": self.poi_strategy_enabled.get(high_type, False),
                "low_display": self.poi_display_enabled.get(low_type, False),
                "low_strategy": self.poi_strategy_enabled.get(low_type, False),
            })
        return rows



    @rx.var
    def poi_zone_type_rows(self) -> list[dict]:
        return [{
            "type": t, "label": label,
            "display": self.poi_display_enabled.get(t, False),
            "strategy": self.poi_strategy_enabled.get(t, False),
        } for t, label in POI_ZONE_TYPES]



    @rx.var
    def poi_zone_source_tf_rows(self) -> list[dict]:
        return [{"tf": tf, "enabled": self.poi_zone_source_tf_enabled.get(tf, False)} for tf in POI_LINE_TF_ORDER]
