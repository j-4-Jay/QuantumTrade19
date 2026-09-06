"""Trading Panel page - Futures-only chart foundation.

PATH: ui/pages/trading_panel.py (REPLACE ENTIRE FILE)

FIX (Bulk Controls renamed + re-scoped) - buttons now read "Hide Extras",
"Show Extras", "Enable Default Strategy", "Disable All Strategy" and
call the renamed/re-scoped AppState handlers (poi_hide_extras/
poi_show_extras replace poi_show_all/poi_hide_all - see
poi_settings_mixin.py for the new semantics).
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState, TRADING_PANEL_TF_OPTIONS
from ui.components.trading_panel_chart import trading_panel_chart
from ui.theme.glass import GLASS_CARD_3XL_STYLE


def _ohlc_pill(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, font_size="0.7rem", color="var(--qt19-text-muted)"),
        rx.text(value, font_size="0.82rem", font_weight="700"),
        spacing="1",
    )


def _tf_buttons() -> rx.Component:
    return rx.hstack(
        *[
            rx.button(
                tf,
                size="1",
                variant=rx.cond(AppState.trading_panel_chart_tf == tf, "solid", "outline"),
                on_click=AppState.set_trading_panel_chart_tf(tf),
            )
            for tf in TRADING_PANEL_TF_OPTIONS
        ],
        spacing="1",
    )


def _display_last_group() -> rx.Component:
    return rx.hstack(
        rx.text("Display Last:", font_size="0.78rem", color="var(--qt19-text-muted)"),
        rx.input(
            value=AppState.trading_panel_display_days_draft,
            on_change=AppState.set_trading_panel_display_days_draft,
            on_blur=AppState.commit_trading_panel_display_days,
            on_key_down=AppState.handle_display_days_keydown,
            width="60px",
            size="1",
        ),
        rx.text("Days", font_size="0.78rem", color="var(--qt19-text-muted)"),
        rx.text(
            f"\u2022 QT19 DB: {AppState.trading_panel_local_days}d",
            font_size="0.75rem", color="var(--qt19-text-muted)",
        ),
        spacing="2",
        align_items="center",
    )


def _bulk_controls_toggle_button() -> rx.Component:
    return rx.tooltip(
        rx.icon_button(
            rx.icon("list-checks", size=16),
            on_click=AppState.toggle_trading_panel_bulk_controls,
            variant=rx.cond(AppState.trading_panel_bulk_controls_visible, "solid", "outline"),
            size="1",
            border_radius="9999px",
        ),
        content="POI bulk controls",
    )


def _header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.select(
                AppState.trading_panel_symbol_options,
                value=AppState.trading_panel_symbol,
                on_change=AppState.set_trading_panel_symbol,
                width="170px",
            ),
            _tf_buttons(),
            _display_last_group(),
            _bulk_controls_toggle_button(),
            rx.spacer(),
            _ohlc_pill("O", AppState.trading_panel_current_open),
            _ohlc_pill("H", AppState.trading_panel_current_high),
            _ohlc_pill("L", AppState.trading_panel_current_low),
            _ohlc_pill("C", AppState.trading_panel_current_close),
            _ohlc_pill("Closes in", AppState.trading_panel_countdown_text),
            rx.badge(AppState.ws_status, variant="soft"),
            width="100%",
            align_items="center",
            spacing="4",
            wrap="wrap",
        ),
        style={**GLASS_CARD_3XL_STYLE, "padding": "0.9rem 1.1rem"},
        width="100%",
        flex_shrink="0",
    )


def _bulk_controls_strip() -> rx.Component:
    return rx.cond(
        AppState.trading_panel_bulk_controls_visible,
        rx.box(
            rx.flex(
                rx.text("POI Bulk Controls:", font_size="0.78rem", font_weight="700", color="var(--qt19-text-muted)"),
                rx.button("Hide Extras", on_click=AppState.poi_hide_extras, size="1", variant="soft"),
                rx.button("Show Extras", on_click=AppState.poi_show_extras, size="1", variant="soft"),
                rx.button("Enable Default Strategy", on_click=AppState.poi_enable_default_strategy, size="1", variant="soft"),
                rx.button("Disable All Strategy", on_click=AppState.poi_disable_all_strategy, size="1", variant="soft"),
                spacing="2", align_items="center", wrap="wrap",
            ),
            style={**GLASS_CARD_3XL_STYLE, "padding": "0.6rem 1.1rem"},
            width="100%",
            flex_shrink="0",
        ),
    )


def _chart_card() -> rx.Component:
    return rx.box(
        rx.box(
            trading_panel_chart(),
            on_double_click=AppState.reset_trading_panel_view,
            width="100%",
            height="100%",
        ),
        style={
            **GLASS_CARD_3XL_STYLE,
            "padding": "0.9rem",
            "display": "flex",
            "flex_direction": "column",
            "height": "100%",
        },
        width="100%",
        flex="1",
        min_height="0",
    )


def trading_panel_page() -> rx.Component:
    return rx.vstack(
        _header(),
        _bulk_controls_strip(),
        _chart_card(),
        spacing="3",
        width="100%",
        height="100%",
        flex="1",
        min_height="0",
        overflow="hidden",
    )
