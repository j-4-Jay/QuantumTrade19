"""Trading Panel interactive candlestick chart component.

PATH: ui/components/trading_panel_chart.py  (REPLACE ENTIRE FILE)

FIX v0.5.0 - passes AppState.poi_chart_overlays / poi_chart_overlays_version
through to KLineChart's new poi_overlays / poi_overlays_version props (see
ui/components/kline_chart.py's v0.5.0 docstring) - this is what actually
puts POI lines/zones on the chart.

FIX v0.4.59 (carried forward, unchanged) - passes AppState.trading_panel_data_version
through to KLineChart's data_version prop - fixes the infinite
subscribeBar/unsubscribeBar teardown loop that kept the live price line
permanently disconnected.

CHANGE (v0.3.8, carried forward): passes on_context_menu through to the
real Reflex event trigger declared on KLineChart.
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from state.app_state_mixins.shared import TRADING_PANEL_CHART_ID
from ui.components.kline_chart import kline_chart


def trading_panel_chart() -> rx.Component:
    """Render the interactive KLineCharts surface."""
    return rx.box(
        kline_chart(
            data=AppState.trading_panel_candles,
            data_version=AppState.trading_panel_data_version,
            symbol=AppState.trading_panel_symbol_info,
            period=AppState.trading_panel_period,
            styles=AppState.trading_panel_styles,
            poi_overlays=AppState.poi_chart_overlays,
            poi_overlays_version=AppState.poi_chart_overlays_version,
            chart_id=TRADING_PANEL_CHART_ID,
            id=TRADING_PANEL_CHART_ID,
            on_context_menu=AppState.open_trading_panel_menu,
            style={
                "width": "100%",
                "height": "100%",
                "min_height": "0",
                "border_radius": "14px",
                "border": "1px solid rgba(147, 173, 205, 0.18)",
                "background": rx.cond(
                    AppState.trading_panel_chart_theme == "day",
                    "#f7f9fc",
                    "#101722",
                ),
            },
        ),
        width="100%",
        height="100%",
        min_height="0",
        flex="1",
    )
