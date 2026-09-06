"""Trading Panel interactive candlestick chart component.

PATH: ui/components/trading_panel_chart.py  (REPLACE ENTIRE FILE)

FIX (auto-theme chart background) - background now comes from
AppState.trading_panel_bg_color (auto-follows the app's current theme,
or an explicit override chosen via the right-click "Change Mode"
submenu) instead of a hardcoded day/night pair of hex colors.
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
            poi_dots=AppState.poi_dots,
            poi_dots_version=AppState.poi_dots_version,
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
