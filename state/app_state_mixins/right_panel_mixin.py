"""Executable AppState mixin: Trading Panel right sidebar (FT-U.3a).

PATH: state/app_state_mixins/right_panel_mixin.py  (NEW FILE)

Keeps only the screen state of the floating right sidebar: open or closed
and the active tab. Nothing is saved to the settings file yet.
"""
from __future__ import annotations

import reflex as rx

_RIGHT_TABS = ["Trade", "POI", "Setups", "Alerts"]


class RightPanelMixin(rx.State, mixin=True):
    right_panel_open: bool = True
    right_panel_tab: str = "Trade"
    bottom_panel_open: bool = True

    def _remember_panel(self, key: str, value) -> None:
        try:
            from state.app_state_mixins.shared import _engine
            _engine.security.persistence.save({key: value})
        except Exception:
            __import__("logging").getLogger("right_panel").exception("panel_memory_save_failed key=%s", key)

    def _restore_panel_memory(self, settings: dict) -> None:
        self.right_panel_open = bool(settings.get("right_panel_open", True))
        tab = settings.get("right_panel_tab", "Trade")
        self.right_panel_tab = tab if tab in _RIGHT_TABS else "Trade"
        self.bottom_panel_open = bool(settings.get("bottom_panel_open", True))

    def toggle_right_panel(self) -> None:
        self.right_panel_open = not self.right_panel_open
        self._remember_panel("right_panel_open", self.right_panel_open)

    def set_right_tab(self, tab: str) -> None:
        if tab in _RIGHT_TABS:
            self.right_panel_tab = tab
            self._remember_panel("right_panel_tab", tab)

    def toggle_bottom_panel(self) -> None:
        self.bottom_panel_open = not self.bottom_panel_open
        self._remember_panel("bottom_panel_open", self.bottom_panel_open)
