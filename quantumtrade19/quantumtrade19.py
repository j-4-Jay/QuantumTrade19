"""QuantumTrade19 - Reflex application entrypoint.

PATCH: initialize persistent runtime logging before Reflex can create
background tasks, Workers, or thread pools. configure_logging() is idempotent
and writes logs/quantumtrade19.log plus logs/errors.log.
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
    )


app = rx.App()
app.add_page(index, route="/", on_load=AppState.on_load, title="QuantumTrade19")
