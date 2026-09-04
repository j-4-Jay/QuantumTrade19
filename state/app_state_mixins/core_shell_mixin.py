"""Executable AppState mixin: core shell, splash, transitions, tabs, and sounds.

PATH: state/app_state_mixins/core_shell_mixin.py  (REPLACE ENTIRE FILE)

FIX v0.4.41 - "live chart only updates on tab switch" root cause found:
now that active_tab correctly persists (v0.4.36), a restart/reload that
lands directly on "Trading Panel" or "Settings" NEVER started their
background pollers - that only ever happened inside set_active_tab(),
which on_load() does not call (it restores active_tab directly). Fixed by
having on_load() perform the SAME chart-refresh + poller-start steps
set_active_tab() does, for whichever tab was actually restored.

FIX v0.4.41 - Settings sub-tab (Appearance/Data & Connection/Security/
Trading Defaults) was never persisted at all - added
settings_active_subtab, restored in on_load() and saved in the new
set_settings_active_subtab().

FIX v0.4.36 (carried forward) - active_tab itself now round-trips through
persistence.save()/on_load() exactly like every other shell setting.
"""
from __future__ import annotations

import asyncio

import reflex as rx

from config.settings import TRADING_PANEL_DEFAULT_DISPLAY_DAYS
from state.app_state_mixins.shared import (
    _engine,
    SHELL_STATE_CLASS,
    SIDEBAR_TABS,
    SPLASH_DURATION_SECONDS,
    SPLASH_HOLD_SECONDS,
    THEMES,
    THEME_LABELS,
    THEME_ORDER,
    TRANSITION_EFFECTS,
)


class CoreShellMixin(rx.State, mixin=True):
    async def on_load(self) -> None:
        self.theme_key = _engine.ui.theme.get_active_key()
        self.paper_mode = _engine.paper_mode
        self.sound_muted = not _engine.ui.sound.is_master_on()
        settings = _engine.security.persistence.load()

        self.active_tab = settings.get("active_tab", self.active_tab)
        self.settings_active_subtab = settings.get("settings_active_subtab", self.settings_active_subtab)
        self.transition_effects_enabled = settings.get("transition_effects_enabled", self.transition_effects_enabled)
        self.transition_mode = settings.get("transition_mode", self.transition_mode)
        self.tab_transition_effects_enabled = settings.get("tab_transition_effects_enabled", self.tab_transition_effects_enabled)
        self.tab_transition_mode = settings.get("tab_transition_mode", self.tab_transition_mode)
        self.trading_panel_chart_theme = settings.get("trading_panel_chart_theme", self.trading_panel_chart_theme)
        self.trading_panel_symbol = settings.get("trading_panel_symbol", self.trading_panel_symbol)
        self.trading_panel_chart_tf = settings.get("trading_panel_chart_tf", self.trading_panel_chart_tf)
        self.sidebar_collapsed = bool(settings.get("sidebar_collapsed", False))

        saved_days = settings.get(f"chart_display_days::{self.trading_panel_symbol}", TRADING_PANEL_DEFAULT_DISPLAY_DAYS)
        self.trading_panel_display_days_input = str(saved_days)
        self.trading_panel_display_days_draft = str(saved_days)

        _engine.ensure_market_data_started()
        self.refresh_symbol_rows()

        background_tasks = [type(self).start_poi_monitor_background, type(self).poll_deep_history_cards]
        if self.active_tab == "Trading Panel":
            self.refresh_trading_panel_chart()
            background_tasks.append(type(self).poll_trading_panel_chart)
        return background_tasks

    @rx.event(background=True)
    async def start_poi_monitor_background(self):
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

    def set_active_tab(self, tab: str) -> None:
        self.active_tab = tab
        _engine.security.persistence.save({"active_tab": tab})
        self.detail_popup_open = False
        self._pick_tab_transition_effect()
        if tab == "Trading Panel":
            self.refresh_trading_panel_chart()
            return [self.play_sound("tab-slide"), type(self).poll_trading_panel_chart]
        if tab == "Settings":
            return [self.play_sound("tab-slide"), type(self).poll_deep_history_cards]
        return self.play_sound("tab-slide")

    def set_settings_active_subtab(self, subtab: str) -> None:
        """Persists which Settings sub-tab (Appearance / Data & Connection /
        Security & Notifications / Trading Defaults) was last open, so it
        is restored on the next app restart - same pattern as active_tab."""
        self.settings_active_subtab = subtab
        _engine.security.persistence.save({"settings_active_subtab": subtab})

    def set_theme(self, key: str) -> None:
        if _engine.ui.theme.set_active_key(key):
            self.theme_key = key

    def toggle_sound(self) -> None:
        is_on = _engine.ui.sound.toggle_master()
        self.sound_muted = not is_on

    def toggle_sidebar_collapsed(self) -> None:
        self.sidebar_collapsed = not self.sidebar_collapsed
        _engine.security.persistence.save({"sidebar_collapsed": self.sidebar_collapsed})

    def play_sound(self, event_name: str):
        url = _engine.ui.play_sound(event_name)
        if not url:
            return
        return rx.call_script(
            f"(function(){{ try {{ new Audio('{url}').play().catch(function(){{}}); }} "
            f"catch(e) {{}} }})();"
        )

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
            "accent": t.accent,
            "accent_glow": t.accent_glow,
            "bg_from": t.bg_from,
            "bg_to": t.bg_to,
            "glass_bg": t.glass_bg,
            "glass_border": t.glass_border,
            "text_primary": t.text_primary,
            "text_muted": t.text_muted,
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
