"""Trading Panel interactive candlestick chart component.

PATH: ui/components/trading_panel_chart.py  (REPLACE ENTIRE FILE)

FIX (File 04.1 - Setup Visualization) - poi_overlays/poi_dots swapped for
AppState.combined_chart_overlays / AppState.combined_chart_dots (and their
matching *_version counters), which is just POI overlays/dots (unchanged)
PLUS the new confirmed/pending 123Bull/123Bear setup markers from
setup_visualization_mixin.py, concatenated together. kline_chart.py itself
is UNCHANGED - it already renders these generically (kind="zone" for the
candle-highlight, plain dots for the Candle3 icon / pending marker).

Carried forward unchanged: background still comes from
AppState.trading_panel_bg_color (auto-follows the app's current theme, or
an explicit override chosen via the right-click "Change Mode" submenu).
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
            poi_overlays=AppState.combined_chart_overlays,
            poi_overlays_version=AppState.combined_chart_overlays_version,
            poi_dots=AppState.combined_chart_dots,
            poi_dots_version=AppState.combined_chart_dots_version,
            chart_id=TRADING_PANEL_CHART_ID,
            id=TRADING_PANEL_CHART_ID,
            on_context_menu=AppState.open_trading_panel_menu,
            style={
                "width": "100%",
                "height": "100%",
                "min_height": "0",
                "border_radius": "14px",
                "border": "1px solid rgba(147, 173, 205, 0.18)",
                "background": AppState.trading_panel_bg_color,
            },
        ),
        width="100%",
        height="100%",
        min_height="0",
        flex="1",
    )
