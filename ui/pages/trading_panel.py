"""Trading Panel page - Futures-only chart foundation.

PATH: ui/pages/trading_panel.py (REPLACE ENTIRE FILE)

FIX v0.4.57 - removed the hover-glow effect from both Trading Panel cards
(_header() and _chart_card()) entirely, per request - reverted from
qt19_glow_card() back to a plain rx.box with GLASS_CARD_3XL_STYLE. The
sidebar's glow (ui/components/sidebar.py) is untouched - this change is
scoped only to this page.

FIX v0.4.46 (carried forward): Row 2 removed; Display Last + QT19 DB days
folded into the header row; chart card expands to fill remaining page
height via flex="1"/min_height="0".

FIX v0.4.43 (carried forward): countdown-to-candle-close text next to the
OHLC pills, labeled "Closes in".
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
        _chart_card(),
        spacing="3",
        width="100%",
        height="100%",
        flex="1",
        min_height="0",
        overflow="hidden",
    )
