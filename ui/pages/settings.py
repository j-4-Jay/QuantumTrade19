"""Settings tab - App-Shell placeholder page, now tab-segregated + grid-arranged.

PATH: ui/pages/settings.py (REPLACE ENTIRE FILE)

FIX (merged cards) - poi_vertical_markers_card import/usage REMOVED - its
settings are now inside poi_lines_card() per-TF. Grid updated accordingly
(one fewer full-row card).
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE
from ui.components.deep_historical_data_card import deep_historical_data_card
from ui.components.poi_engine_settings_card import (
    poi_timezone_card,
    poi_lines_card,
    poi_horizontal_style_card,
    poi_zone_matrix_card,
    poi_zone_types_card,
    poi_custom_lines_card,
    poi_visual_controls_card,
)

_SCROLL_CONTENT_STYLE = {
    "overflow_y": "auto",
    "overflow_x": "hidden",
    "flex": "1",
    "min_height": "0",
    "width": "100%",
}


def _effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_transition_effect(opt["key"], checked),
        ),
        rx.text(opt["label"], font_size="0.82rem", color="var(--qt19-text-primary)"),
        spacing="2", align_items="center", width="100%",
    )


def _tab_effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.tab_transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_tab_transition_effect(opt["key"], checked),
        ),
        rx.text(opt["label"], font_size="0.82rem", color="var(--qt19-text-primary)"),
        spacing="2", align_items="center", width="100%",
    )


def _transition_effects_card() -> rx.Component:
    return rx.vstack(
        rx.heading("Login \u2192 Dashboard Transition", size="4", color="var(--qt19-text-primary)"),
        rx.text("Pick which entrance animations are allowed, and how they're chosen each time you log in.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600", color="var(--qt19-text-primary)"),
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
        rx.heading("Tab Switch Animation", size="4", color="var(--qt19-text-primary)"),
        rx.text("Controls the effect used when switching between Dashboard, Trading Panel, "
                "Journal & Reports, Alerts, and Settings.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600", color="var(--qt19-text-primary)"),
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
        rx.heading(title, size="4", color="var(--qt19-text-primary)"),
        rx.text(note, font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.badge("Coming in a later module", variant="soft", margin_top="0.5rem"),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _crosshair_settings_card() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Crosshair", size="4", color="var(--qt19-text-primary)"),
            rx.spacer(),
            rx.hstack(
                rx.text("On", font_size="0.78rem", color="var(--qt19-text-muted)"),
                rx.switch(checked=AppState.trading_panel_crosshair_enabled, on_change=AppState.toggle_trading_panel_crosshair),
                spacing="2", align_items="center",
            ),
            width="100%", align_items="center",
        ),
        rx.text("Controls the Trading Panel chart's crosshair lines.", font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Color:", font_size="0.82rem", font_weight="600"),
            rx.input(type="color", value=AppState.trading_panel_crosshair_color, on_change=AppState.set_trading_panel_crosshair_color, width="40px", height="30px", padding="0", border="none", cursor="pointer"),
            rx.text("Style:", font_size="0.82rem", font_weight="600", margin_left="1rem"),
            rx.segmented_control.root(
                rx.segmented_control.item("Dotted", value="dotted"),
                rx.segmented_control.item("Solid", value="solid"),
                value=AppState.trading_panel_crosshair_style, on_change=AppState.set_trading_panel_crosshair_style, size="1",
            ),
            spacing="3", align_items="center", margin_top="0.5rem", wrap="wrap",
        ),
        rx.vstack(
            rx.text(f"Transparency: {AppState.trading_panel_crosshair_opacity}%", font_size="0.78rem"),
            rx.slider(default_value=[AppState.trading_panel_crosshair_opacity], on_value_commit=AppState.set_trading_panel_crosshair_opacity, min=0, max=100, width="100%"),
            spacing="1", width="100%", margin_top="0.5rem",
        ),
        rx.vstack(
            rx.text(f"Thickness: {AppState.trading_panel_crosshair_thickness}px", font_size="0.78rem"),
            rx.slider(default_value=[AppState.trading_panel_crosshair_thickness], on_value_commit=AppState.set_trading_panel_crosshair_thickness, min=1, max=4, width="100%"),
            spacing="1", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _swatch(label: str, value: str, on_change) -> rx.Component:
    return rx.hstack(
        rx.input(type="color", value=value, on_change=on_change, width="34px", height="28px", padding="0", border="none", cursor="pointer"),
        rx.text(label, font_size="0.76rem"),
        spacing="2", align_items="center",
    )


def _candle_style_settings_card() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Candle Style", size="4", color="var(--qt19-text-primary)"),
            rx.spacer(),
            rx.button("Reset to Premium Defaults", on_click=AppState.reset_candle_style_defaults, size="1", variant="soft"),
            width="100%", align_items="center", wrap="wrap",
        ),
        rx.text(
            "\u201cGradient fill\u201d isn't offered - the chart library only supports solid "
            "colors natively. The premium look comes from a brighter border than the fill.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.hstack(
            rx.text("Body Type:", font_size="0.82rem", font_weight="600"),
            rx.select(
                ["Solid", "Hollow (all)", "Up Hollow", "Down Hollow"],
                value=rx.match(
                    AppState.candle_style_mode,
                    ("solid", "Solid"), ("hollow", "Hollow (all)"),
                    ("up_hollow", "Up Hollow"), ("down_hollow", "Down Hollow"),
                    "Solid",
                ),
                on_change=lambda v: AppState.set_candle_style_mode(
                    rx.match(v, ("Solid", "solid"), ("Hollow (all)", "hollow"), ("Up Hollow", "up_hollow"), ("Down Hollow", "down_hollow"), "solid")
                ),
                width="160px",
            ),
            spacing="3", align_items="center", margin_top="0.5rem",
        ),
        rx.grid(
            rx.vstack(
                rx.text("Up (Bullish)", font_size="0.82rem", font_weight="700", color="#16C784"),
                _swatch("Fill", AppState.candle_up_color, AppState.set_candle_up_color),
                _swatch("Border", AppState.candle_up_border_color, AppState.set_candle_up_border_color),
                _swatch("Wick", AppState.candle_up_wick_color, AppState.set_candle_up_wick_color),
                spacing="2", width="100%", padding="0.6rem 0.7rem",
                style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
            ),
            rx.vstack(
                rx.text("Down (Bearish)", font_size="0.82rem", font_weight="700", color="#EA3943"),
                _swatch("Fill", AppState.candle_down_color, AppState.set_candle_down_color),
                _swatch("Border", AppState.candle_down_border_color, AppState.set_candle_down_border_color),
                _swatch("Wick", AppState.candle_down_wick_color, AppState.set_candle_down_wick_color),
                spacing="2", width="100%", padding="0.6rem 0.7rem",
                style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="3", width="100%", margin_top="0.5rem",
        ),
        rx.hstack(
            rx.text("No-Change Color:", font_size="0.78rem", font_weight="600"),
            rx.input(type="color", value=AppState.candle_no_change_color, on_change=AppState.set_candle_no_change_color, width="34px", height="28px", padding="0", border="none", cursor="pointer"),
            spacing="2", align_items="center", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _appearance_tab() -> rx.Component:
    return rx.grid(
        _transition_effects_card(),
        _tab_transition_card(),
        _coming_soon_card("Theme", "6 selectable themes (Yellow/Saffron/Blue x Day/Night)."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
        spacing="2", width="100%", margin_top="0.5rem", padding_bottom="1.5rem",
    )


def _data_connection_tab() -> rx.Component:
    return rx.grid(
        deep_historical_data_card(),
        _coming_soon_card("Symbols & Rows", "Choose which symbols appear on the Dashboard."),
        _coming_soon_card("Tick Bands & Alerts", "Per-symbol tick-size and alert-band configuration."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="2"),
        spacing="2", width="100%", margin_top="0.5rem", padding_bottom="1.5rem",
    )


def _security_tab() -> rx.Component:
    return rx.grid(
        _coming_soon_card("Login & 2FA", "Manage password and TOTP authenticator settings."),
        _coming_soon_card("Notification Channels", "Telegram / Discord multi-recipient setup."),
        _coming_soon_card("Startup & Tray", "Run-on-startup and system tray behavior."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
        spacing="2", width="100%", margin_top="0.5rem", padding_bottom="1.5rem",
    )


def _trading_tab() -> rx.Component:
    _full_row = {"grid_column": "1 / -1"}
    return rx.grid(
        poi_timezone_card(),
        _crosshair_settings_card(),
        _candle_style_settings_card(),
        rx.box(poi_lines_card(), style=_full_row, width="100%"),
        poi_horizontal_style_card(),
        poi_zone_matrix_card(),
        rx.box(poi_zone_types_card(), style=_full_row, width="100%"),
        poi_custom_lines_card(),
        poi_visual_controls_card(),
        _coming_soon_card("Signal Bias Filter", "Market-aware auto-disable rules for filters."),
        _coming_soon_card("Paper Trading", "Paper/Live toggle defaults and simulator settings."),
        columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
        spacing="2", width="100%", margin_top="0.5rem", padding_bottom="1.5rem",
    )


def settings_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Settings", size="6", color="var(--qt19-text-primary)", flex_shrink="0"),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Appearance", value="appearance", color="var(--qt19-text-primary)"),
                rx.tabs.trigger("Data & Connection", value="data", color="var(--qt19-text-primary)"),
                rx.tabs.trigger("Security & Notifications", value="security", color="var(--qt19-text-primary)"),
                rx.tabs.trigger("Trading Defaults", value="trading", color="var(--qt19-text-primary)"),
                flex_shrink="0",
            ),
            rx.tabs.content(_appearance_tab(), value="appearance", style=_SCROLL_CONTENT_STYLE),
            rx.tabs.content(_data_connection_tab(), value="data", style=_SCROLL_CONTENT_STYLE),
            rx.tabs.content(_security_tab(), value="security", style=_SCROLL_CONTENT_STYLE),
            rx.tabs.content(_trading_tab(), value="trading", style=_SCROLL_CONTENT_STYLE),
            value=AppState.settings_active_subtab,
            on_change=AppState.set_settings_active_subtab,
            width="100%",
            height="100%",
            display="flex",
            flex_direction="column",
            overflow="hidden",
        ),
        width="100%", height="100%", spacing="3",
        display="flex", flex_direction="column", overflow="hidden",
        on_mount=AppState.load_poi_settings,
    )
