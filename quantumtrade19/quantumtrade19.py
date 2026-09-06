"""QuantumTrade19 - Reflex application entrypoint.

PATH: quantumtrade19/quantumtrade19.py  (REPLACE ENTIRE FILE)

FIX (canvas background per page + no page-level scroll) - the per-tab
content wrapper's `overflow_y="auto"` (which used to let the WHOLE page
scroll as one region) is now `overflow="hidden"` - scrolling now only
ever happens INSIDE a page's own cards (see dashboard.py/journal.py/
alerts.py/settings.py), never at the page level. Also added a per-tab
canvas background (_CANVAS_BG_FOR_TAB) applied to this same wrapper, so
each page sits on its own distinct, fixed backdrop that cards visually
float on top of - this background never scrolls since the wrapper that
carries it no longer scrolls either.

FIX v0.4.48 (carried forward) - this wrapper has height="100%", flex="1",
min_height="0" so Trading Panel's chart can fill available height;
display=flex/flex_direction=column preserved.

CHANGE (v0.3.8.2, unchanged): trading_panel_context_menu() stays mounted
as a direct sibling of the main transformed screen box.
"""
from __future__ import annotations


from config.logging_config import configure_logging


configure_logging()


import reflex as rx


from state.app_state import AppState
from ui.theme.global_css import qt19_global_css
from ui.components.keyboard_shortcuts import qt19_keyboard_shortcuts
from ui.components.autofill_sync import qt19_autofill_sync
from ui.components.trading_panel_context_menu import trading_panel_context_menu
from ui.pages.splash import splash_screen
from ui.pages.register import register_screen
from ui.pages.login import login_screen
from ui.pages.forgot_password import forgot_password_screen
from ui.pages.manage_security import manage_security_screen
from ui.pages.app_lock import app_lock_screen
from ui.pages.dashboard import dashboard_page
from ui.pages.trading_panel import trading_panel_page
from ui.pages.journal import journal_page
from ui.pages.alerts import alerts_page
from ui.pages.settings import settings_page
from ui.components.page_shell import qt19_page_shell
from ui.components.symbol_detail_popup import symbol_detail_popup


# One distinct, FIXED canvas background per page - never scrolls (the
# wrapper carrying this background no longer scrolls at all; only
# individual cards inside each page scroll their own content).
_CANVAS_BG_FOR_TAB = {
    "Dashboard": "radial-gradient(circle at 15% 0%, rgba(120,170,255,0.05) 0%, transparent 55%)",
    "Trading Panel": "radial-gradient(circle at 85% 0%, rgba(120,255,180,0.05) 0%, transparent 55%)",
    "Journal & Reports": "radial-gradient(circle at 15% 100%, rgba(255,190,120,0.05) 0%, transparent 55%)",
    "Alerts": "radial-gradient(circle at 85% 100%, rgba(255,120,140,0.05) 0%, transparent 55%)",
    "Settings": "radial-gradient(circle at 50% 50%, rgba(180,140,255,0.05) 0%, transparent 60%)",
}


def _canvas_background() -> rx.Var:
    return rx.match(
        AppState.active_tab,
        *[(tab, bg) for tab, bg in _CANVAS_BG_FOR_TAB.items()],
        "transparent",
    )


def _shell_body() -> rx.Component:
    return rx.fragment(
        rx.box(
            rx.cond(AppState.active_tab == "Dashboard", dashboard_page()),
            rx.cond(AppState.active_tab == "Trading Panel", trading_panel_page()),
            rx.cond(AppState.active_tab == "Journal & Reports", journal_page()),
            rx.cond(AppState.active_tab == "Alerts", alerts_page()),
            rx.cond(AppState.active_tab == "Settings", settings_page()),
            key=AppState.active_tab,
            class_name="qt19-transition-" + AppState.tab_transition_active_effect,
            width="100%",
            height="100%",
            flex="1",
            min_height="0",
            display="flex",
            flex_direction="column",
            overflow="hidden",
            background=_canvas_background(),
        ),
        symbol_detail_popup(),
    )



def _current_screen() -> rx.Component:
    return rx.cond(
        AppState.screen == "splash",
        splash_screen(),
        rx.cond(
            AppState.screen == "register",
            register_screen(),
            rx.cond(
                AppState.screen == "login",
                login_screen(),
                rx.cond(
                    AppState.screen == "manage_security",
                    manage_security_screen(),
                    rx.cond(
                        AppState.screen == "forgot_password",
                        forgot_password_screen(),
                        rx.cond(
                            AppState.screen == "locked",
                            app_lock_screen(),
                            qt19_page_shell(_shell_body()),
                        ),
                    ),
                ),
            ),
        ),
    )



def index() -> rx.Component:
    return rx.fragment(
        qt19_global_css(),
        qt19_keyboard_shortcuts(),
        qt19_autofill_sync(),
        rx.box(
            _current_screen(),
            class_name="qt19-transition-" + AppState.transition_active_effect,
            key=AppState.screen,
            style={
                "--qt19-accent": AppState.theme_vars["accent"],
                "--qt19-accent-glow": AppState.theme_vars["accent_glow"],
                "--qt19-bg-from": AppState.theme_vars["bg_from"],
                "--qt19-bg-to": AppState.theme_vars["bg_to"],
                "--qt19-glass-bg": AppState.theme_vars["glass_bg"],
                "--qt19-glass-border": AppState.theme_vars["glass_border"],
                "--qt19-text-primary": AppState.theme_vars["text_primary"],
                "--qt19-text-muted": AppState.theme_vars["text_muted"],
            },
            width="100%",
            height="100vh",
        ),
        trading_panel_context_menu(),
    )



app = rx.App()
app.add_page(index, route="/", on_load=AppState.on_load, title="QuantumTrade19")
