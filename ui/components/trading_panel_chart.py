"""Trading Panel interactive candlestick chart component.

PATH: ui/components/trading_panel_chart.py
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from ui.components.kline_chart import kline_chart


KLINE_CONTROL_ID = "qt19-trading-panel-kline"


def trading_panel_chart() -> rx.Component:
    """Render the browser-local interactive KLineCharts surface."""
    return rx.box(
        kline_chart(
            data=AppState.trading_panel_candles,
            symbol=AppState.trading_panel_symbol_info,
            period=AppState.trading_panel_period,
            control_id=KLINE_CONTROL_ID,
            id=KLINE_CONTROL_ID,
            style={
                "width": "100%",
                "height": "520px",
                "min_height": "520px",
                "border_radius": "14px",
                "border": "1px solid rgba(147, 173, 205, 0.18)",
                "background": "#101722",
            },
        ),
        width="100%",
        height="520px",
    )
