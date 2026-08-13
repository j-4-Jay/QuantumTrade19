"""Reflex State - thin UI binding layer over the Master App Engine (no business logic here).

PATH: state/app_state.py  (REPLACE ENTIRE FILE)

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

    transition_effects_enabled: list[str] = ["dissolve", "zoom-in", "slide-up", "flip-x", "blur-in"]
    transition_mode: str = "shuffle"
    transition_active_effect: str = "dissolve"
    _transition_sequence_index: int = 0
    _splash_task_running: bool = False

    def on_load(self) -> None:
        self.theme_key = _engine.ui.theme.get_active_key()
        self.paper_mode = _engine.paper_mode
        self.sound_muted = not _engine.ui.sound.is_master_on()
        settings = _engine.security.persistence.load()
        self.transition_effects_enabled = settings.get("transition_effects_enabled", self.transition_effects_enabled)
        self.transition_mode = settings.get("transition_mode", self.transition_mode)

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
            self.totp_required = _engine.security.is_totp_enabled()
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
        pool = self.transition_effects_enabled or ["dissolve"]
        if self.transition_mode == "single":
            self.transition_active_effect = pool[0]
        elif self.transition_mode == "sequential":
            idx = self._transition_sequence_index % len(pool)
            self.transition_active_effect = pool[idx]
            self._transition_sequence_index = idx + 1
        else:
            self.transition_active_effect = random.choice(pool)

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

    def submit_login(self) -> None:
        if not self.login_username.strip() or len(self.login_password) < 4:
            self.login_error = "Enter your username and password."
            return
        ok = _engine.attempt_login(self.login_username, self.login_password, self.login_totp or None)
        if ok:
            self.login_error = ""
            self.login_password = ""
            self.login_totp = ""
            self.login_credentials_match = False
            self._pick_transition_effect()
            self.screen = _engine.screen.value
        else:
            self.login_error = "Invalid credentials or authenticator code."

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

    def set_theme(self, key: str) -> None:
        if _engine.ui.theme.set_active_key(key):
            self.theme_key = key

    def toggle_sound(self) -> None:
        is_on = _engine.ui.sound.toggle_master()
        self.sound_muted = not is_on

    def toggle_paper_live(self) -> None:
        self.paper_mode = _engine.toggle_paper_live()

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
