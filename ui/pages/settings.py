"""Settings tab - App-Shell placeholder page, now tab-segregated + grid-arranged.

PATH: ui/pages/settings.py (REPLACE ENTIRE FILE)

CHANGE (File 03.1 Scope E): the "POI Timeframes" coming-soon placeholder in
the Trading Defaults tab is now the real POI Engine & Chart Visibility card.

CHANGE (unchanged from before): cards are grouped into logical rx.tabs
matching the categories named in the locked mockup (Appearance, Data &
Connection, and placeholders for categories not yet built), and arranged in
a responsive multi-column grid instead of one full-width vstack.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE
from ui.components.deep_historical_data_card import deep_historical_data_card
from ui.components.poi_engine_settings_card import poi_engine_settings_card



def _effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_transition_effect(opt["key"], checked),
        ),
        rx.text(opt["label"], font_size="0.82rem"),
        spacing="2", align_items="center", width="100%",
    )



def _tab_effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.tab_transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_tab_transition_effect(opt["key"], checked),
        ),
        rx.text(opt["label"], font_size="0.82rem"),
        spacing="2", align_items="center", width="100%",
    )



def _transition_effects_card() -> rx.Component:
    return rx.vstack(
        rx.heading("Login \u2192 Dashboard Transition", size="4"),
        rx.text("Pick which entrance animations are allowed, and how they're chosen each time you log in.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600"),
            rx.select(
                ["single", "sequential", "shuffle"],
                value=AppState.transition_mode,
                on_change=AppState.set_transition_mode,
                width="180px",
            ),
            spacing="3", align_items="center",
        ),
        rx.grid(
            rx.foreach(AppState.transition_effect_options, _effect_checkbox),
            columns="2", spacing="2", width="100%", margin_top="0.5rem",
        ),
        spacing="3", width="100%", style=GLASS_CARD_3XL_STYLE,
    )



def _tab_transition_card() -> rx.Component:
    return rx.vstack(
        rx.heading("Tab Switch Animation", size="4"),
        rx.text("Controls the effect used when switching between Dashboard, Trading Panel, "
                "Journal & Reports, Alerts, and Settings.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600"),
            rx.select(
                ["single", "sequential", "shuffle"],
                value=AppState.tab_transition_mode,
                on_change=AppState.set_tab_transition_mode,
                width="180px",
            ),
            spacing="3", align_items="center",
        ),
        rx.grid(
            rx.foreach(AppState.transition_effect_options, _tab_effect_checkbox),
            columns="2", spacing="2", width="100%", margin_top="0.5rem",
        ),
        spacing="3", width="100%", style=GLASS_CARD_3XL_STYLE,
    )



def _coming_soon_card(title: str, note: str) -> rx.Component:
    return rx.vstack(
        rx.heading(title, size="4"),
        rx.text(note, font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.badge("Coming in a later module", variant="soft", margin_top="0.5rem"),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )



def _appearance_tab() -> rx.Component:
    return rx.grid(
        _transition_effects_card(),
        _tab_transition_card(),
        _coming_soon_card("Theme", "6 selectable themes (Yellow/Saffron/Blue x Day/Night)."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
        spacing="4", width="100%", margin_top="1rem",
    )



def _data_connection_tab() -> rx.Component:
    return rx.grid(
        deep_historical_data_card(),
        _coming_soon_card("Symbols & Rows", "Choose which symbols appear on the Dashboard."),
        _coming_soon_card("Tick Bands & Alerts", "Per-symbol tick-size and alert-band configuration."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="2"),
        spacing="4", width="100%", margin_top="1rem",
    )



def _security_tab() -> rx.Component:
    return rx.grid(
        _coming_soon_card("Login & 2FA", "Manage password and TOTP authenticator settings."),
        _coming_soon_card("Notification Channels", "Telegram / Discord multi-recipient setup."),
        _coming_soon_card("Startup & Tray", "Run-on-startup and system tray behavior."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
        spacing="4", width="100%", margin_top="1rem",
    )



def _trading_tab() -> rx.Component:
    return rx.grid(
        poi_engine_settings_card(),
        _coming_soon_card("Signal Bias Filter", "Market-aware auto-disable rules for filters."),
        _coming_soon_card("Paper Trading", "Paper/Live toggle defaults and simulator settings."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="2"),
        spacing="4", width="100%", margin_top="1rem",
    )



def settings_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Settings", size="6"),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Appearance", value="appearance"),
                rx.tabs.trigger("Data & Connection", value="data"),
                rx.tabs.trigger("Security & Notifications", value="security"),
                rx.tabs.trigger("Trading Defaults", value="trading"),
            ),
            rx.tabs.content(_appearance_tab(), value="appearance"),
            rx.tabs.content(_data_connection_tab(), value="data"),
            rx.tabs.content(_security_tab(), value="security"),
            rx.tabs.content(_trading_tab(), value="trading"),
            default_value="appearance",
            width="100%",
        ),
        width="100%", spacing="3",
    )
