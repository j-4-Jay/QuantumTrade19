"""Trading Panel page - Futures-only chart foundation.

PATH: ui/pages/trading_panel.py (REPLACE ENTIRE FILE)

FIX (File 04.1 - Setup Visualization) - added:
  1. "Detect setups from last N days" numeric input next to Display Last,
     persisted per symbol+timeframe (state/app_state_mixins/setup_visualization_mixin.py,
     same pattern as Display Last X Days).
  2. A compact setup-stats strip (date-wise confirmed Bull / confirmed Bear /
     failed-aborted), sourced only from SetupDetectionMonitor via the new mixin.
Chart markers themselves need NO new UI here - they ride the existing chart
via ui/components/trading_panel_chart.py's combined_chart_overlays/dots.

Does not touch Dashboard/Journal/Alerts pages.

Carried forward unchanged from the prior lock: "Bulk Controls" renamed +
re-scoped buttons (Hide Extras / Show Extras / Enable Default Strategy /
Disable All Strategy).
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


def _setup_lookback_group() -> rx.Component:
    """File 04.1 - "Detect setups from last N days", persisted per
    symbol+timeframe via setup_visualization_mixin.py."""
    return rx.hstack(
        rx.icon("target", size=14, color="var(--qt19-text-muted)"),
        rx.text("Detect setups, last:", font_size="0.78rem", color="var(--qt19-text-muted)"),
        rx.input(
            value=AppState.setup_detect_lookback_days_draft,
            on_change=AppState.set_setup_detect_lookback_draft,
            on_blur=AppState.commit_setup_detect_lookback_days,
            on_key_down=AppState.handle_setup_lookback_keydown,
            width="60px",
            size="1",
        ),
        rx.text("Days", font_size="0.78rem", color="var(--qt19-text-muted)"),
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
            _setup_lookback_group(),
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


def _setup_stat_pill(label: str, value, color: str) -> rx.Component:
    return rx.hstack(
        rx.box(width="8px", height="8px", border_radius="9999px", background=color),
        rx.text(label, font_size="0.72rem", color="var(--qt19-text-muted)"),
        rx.text(value, font_size="0.8rem", font_weight="700"),
        spacing="1",
        align_items="center",
    )


def _setup_stats_row(row: dict) -> rx.Component:
    return rx.hstack(
        rx.text(row["date"], font_size="0.72rem", width="90px", color="var(--qt19-text-muted)"),
        _setup_stat_pill("Bull", row["confirmed_bull"], "#16C784"),
        _setup_stat_pill("Bear", row["confirmed_bear"], "#EA3943"),
        _setup_stat_pill("Failed/Aborted", row["failed_aborted"], "#F5A623"),
        spacing="4",
        align_items="center",
        width="100%",
    )


def _setup_stats_panel() -> rx.Component:
    """File 04.1 compact setup-stats panel - sourced ONLY from
    SetupDetectionMonitor via setup_visualization_mixin.py (no new Worker
    logic, aggregation for display only)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("bar-chart-3", size=14, color="var(--qt19-text-muted)"),
                rx.text("Setup Stats", font_size="0.8rem", font_weight="700"),
                rx.spacer(),
                _setup_stat_pill("Total Bull", AppState.setup_stats_totals["confirmed_bull"], "#16C784"),
                _setup_stat_pill("Total Bear", AppState.setup_stats_totals["confirmed_bear"], "#EA3943"),
                width="100%",
                align_items="center",
            ),
            rx.cond(
                AppState.setup_stats_rows.length() > 0,
                rx.vstack(
                    rx.foreach(AppState.setup_stats_rows, _setup_stats_row),
                    spacing="1",
                    width="100%",
                    max_height="120px",
                    overflow_y="auto",
                ),
                rx.text(
                    "No confirmed setups in the selected lookback window yet.",
                    font_size="0.74rem", color="var(--qt19-text-muted)",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        style={**GLASS_CARD_3XL_STYLE, "padding": "0.7rem 1.1rem"},
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
        _bulk_controls_strip(),
        _setup_stats_panel(),
        _chart_card(),
        spacing="3",
        width="100%",
        height="100%",
        flex="1",
        min_height="0",
        overflow="hidden",
    )
