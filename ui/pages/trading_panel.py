"""Trading Panel tab - Futures-only chart foundation.

PATH: ui/pages/trading_panel.py

CHANGE (v0.3.6):
- Removed the unreliable right-click context menu entirely.
- Added always-visible, reliable buttons: Grid On/Off, Reset View,
  Day/Night, Follow Live, Go Live. All are driven either by real reactive
  AppState vars (Grid, Day/Night) or real Chart-instance calls through the
  window.QT19_CHARTS registry (Reset View, Go Live).
- Fixed the Display Last X Days input: now bound to a draft var that
  updates on every keystroke, with an explicit Apply button (and on_blur)
  to commit + trigger the actual reload. It no longer gets stuck.
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
                variant=rx.cond(
                    AppState.trading_panel_chart_tf == tf,
                    "solid",
                    "outline",
                ),
                on_click=AppState.set_trading_panel_chart_tf(tf),
            )
            for tf in TRADING_PANEL_TF_OPTIONS
        ],
        spacing="1",
    )


def _theme_toggle() -> rx.Component:
    return rx.hstack(
        rx.button(
            "Night",
            size="1",
            variant=rx.cond(
                AppState.trading_panel_chart_theme == "night",
                "solid",
                "outline",
            ),
            on_click=AppState.set_trading_panel_chart_theme("night"),
        ),
        rx.button(
            "Day",
            size="1",
            variant=rx.cond(
                AppState.trading_panel_chart_theme == "day",
                "solid",
                "outline",
            ),
            on_click=AppState.set_trading_panel_chart_theme("day"),
        ),
        spacing="1",
    )


def _grid_toggle() -> rx.Component:
    return rx.button(
        rx.cond(AppState.trading_panel_grid_enabled, "Grid: ON", "Grid: OFF"),
        size="1",
        variant=rx.cond(AppState.trading_panel_grid_enabled, "solid", "outline"),
        on_click=AppState.toggle_trading_panel_grid,
    )


def _follow_live_toggle() -> rx.Component:
    return rx.button(
        rx.cond(
            AppState.trading_panel_follow_live,
            "Follow Live: ON",
            "Follow Live: OFF",
        ),
        size="1",
        variant=rx.cond(
            AppState.trading_panel_follow_live,
            "solid",
            "outline",
        ),
        on_click=AppState.toggle_trading_panel_follow_live,
    )


def _reset_view_button() -> rx.Component:
    return rx.button(
        "Reset View",
        size="1",
        variant="outline",
        on_click=AppState.reset_trading_panel_view,
    )


def _go_live_button() -> rx.Component:
    return rx.button(
        "Go to Live",
        size="1",
        variant="outline",
        on_click=AppState.go_live_trading_panel,
    )


def _header() -> rx.Component:
    return rx.hstack(
        rx.select(
            AppState.trading_panel_symbol_options,
            value=AppState.trading_panel_symbol,
            on_change=AppState.set_trading_panel_symbol,
            width="170px",
        ),
        _tf_buttons(),
        rx.spacer(),
        _ohlc_pill("O", AppState.trading_panel_current_open),
        _ohlc_pill("H", AppState.trading_panel_current_high),
        _ohlc_pill("L", AppState.trading_panel_current_low),
        _ohlc_pill("C", AppState.trading_panel_current_close),
        rx.badge(AppState.ws_status, variant="soft"),
        width="100%",
        align_items="center",
        spacing="4",
        wrap="wrap",
    )


def _chart_controls_bar() -> rx.Component:
    return rx.hstack(
        _grid_toggle(),
        _reset_view_button(),
        _theme_toggle(),
        _follow_live_toggle(),
        _go_live_button(),
        spacing="2",
        align_items="center",
        wrap="wrap",
    )


def _display_window_controls() -> rx.Component:
    return rx.hstack(
        rx.text("Display Last:", font_size="0.8rem"),
        rx.input(
            value=AppState.trading_panel_display_days_draft,
            on_change=AppState.set_trading_panel_display_days_draft,
            on_blur=AppState.commit_trading_panel_display_days,
            width="70px",
            size="1",
        ),
        rx.text("Days", font_size="0.8rem"),
        rx.button(
            "Apply",
            size="1",
            variant="outline",
            on_click=AppState.commit_trading_panel_display_days,
        ),
        rx.divider(orientation="vertical", height="1.2rem"),
        rx.text(
            f"Local: {AppState.trading_panel_local_days} days",
            font_size="0.75rem",
            color="var(--qt19-text-muted)",
        ),
        rx.text(
            f"Broker: {AppState.trading_panel_broker_days}",
            font_size="0.75rem",
            color="var(--qt19-text-muted)",
        ),
        rx.cond(
            AppState.trading_panel_notice != "",
            rx.badge(
                AppState.trading_panel_notice,
                color_scheme="orange",
                variant="soft",
            ),
        ),
        spacing="3",
        align_items="center",
        wrap="wrap",
    )


def trading_panel_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Trading Panel", size="6"),
        rx.box(
            _header(),
            _chart_controls_bar(),
            _display_window_controls(),
            trading_panel_chart(),
            spacing="3",
            style=GLASS_CARD_3XL_STYLE,
            width="100%",
            margin_top="1rem",
        ),
        width="100%",
        spacing="3",
    )
