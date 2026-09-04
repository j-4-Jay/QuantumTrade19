"""QuantumTrade19 - Reflex application entrypoint.

PATH: quantumtrade19/quantumtrade19.py  (REPLACE ENTIRE FILE)

FIX v0.4.48 - "Trading Panel chart card stops at row-1 height instead of
filling the page" - found ANOTHER broken link in the height chain (in
addition to the ui/pages/trading_panel.py and trading_panel_chart.py
flex/height fixes already applied): _shell_body()'s per-tab content
wrapper (the rx.box wrapping all five pages) had width="100%" but NO
height at all, so it always sized itself to content height regardless of
what any child page tried to declare - every child's own height="100%"
was resolving against this height-less parent, collapsing to "auto"
every time. Added height="100%", flex="1", min_height="0", display=flex/
flex_direction=column, and overflow_y="auto" (so Dashboard/Journal/Alerts/
Settings, which are naturally content-height and may exceed the viewport,
can still scroll internally exactly as before - only Trading Panel, which
already declares its own overflow="hidden" internally, actually uses the
new fill-height behavior).

NOTE: this is very likely still not the FULL fix - qt19_page_shell()
(ui/components/page_shell.py) sits between this file's outer
height="100vh" box and this wrapper, and I don't have that file's source
yet. If the chart still doesn't fill the page after this change, that
file is almost certainly the remaining missing link in the chain.

CHANGE (v0.3.8.2, unchanged): trading_panel_context_menu() stays mounted
as a direct sibling of the main transformed screen box, at the true top
level of index()'s returned fragment - NOT nested inside it, so its
position:fixed coordinates are measured from the real viewport instead of
the screen box's own CSS transform context.
"""
from __future__ import annotations

from config.logging_config import configure_logging

# Must run before importing app state/components, which may construct service
# singletons or schedule background work during import/on_load.
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
            overflow_y="auto",
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
