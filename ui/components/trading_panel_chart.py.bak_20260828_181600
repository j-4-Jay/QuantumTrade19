"""Trading Panel interactive candlestick chart component.

PATH: ui/components/trading_panel_chart.py

CHANGE (v0.3.6): styles now comes from AppState.trading_panel_styles, a
computed var that reactively encodes both the Grid on/off setting and the
Day/Night chart theme. This removes the need for any JS-side DOM styling
hacks - toggling grid or theme in AppState now re-renders the chart with the
correct real klinecharts styles automatically.
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
            symbol=AppState.trading_panel_symbol_info,
            period=AppState.trading_panel_period,
            styles=AppState.trading_panel_styles,
            chart_id=TRADING_PANEL_CHART_ID,
            id=TRADING_PANEL_CHART_ID,
            style={
                "width": "100%",
                "height": "520px",
                "min_height": "520px",
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
        height="520px",
    )
