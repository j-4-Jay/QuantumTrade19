"""Shared imports and constants for executable AppState mixins.

PATH: state/app_state_mixins/shared.py
"""
from __future__ import annotations

from engines.masters.master_app_engine import MasterAppEngine, ShellScreen
from config.settings import (
    DEFAULT_THEME_KEY,
    SIDEBAR_TABS,
    SPLASH_DURATION_SECONDS,
    SPLASH_HOLD_SECONDS,
    THEMES,
    THEME_LABELS,
    THEME_ORDER,
    TRANSITION_EFFECTS,
)

_engine = MasterAppEngine()

PINNED_SYMBOL_MAP = {
    "BTCUSD": "B-BTC_USDT",
    "ETHUSD": "B-ETH_USDT",
    "Gold": "B-XAU_USDT",
}

POI_LINE_TF_ORDER = ["1m", "5m", "15m", "1H", "4H", "1D", "1W", "1M"]
POI_LINE_TF_LABELS = {
    "1m": "1 Minute", "5m": "5 Minute", "15m": "15 Minute", "1H": "1 Hour",
    "4H": "4 Hour", "1D": "Daily", "1W": "Weekly", "1M": "Monthly",
}
POI_LINE_TYPE_MAP = {
    "1m": ("P1M_HIGH", "P1M_LOW"), "5m": ("P5M_HIGH", "P5M_LOW"), "15m": ("P15M_HIGH", "P15M_LOW"),
    "1H": ("P1H_HIGH", "P1H_LOW"), "4H": ("4H_HIGH", "4H_LOW"), "1D": ("PDH", "PDL"),
    "1W": ("1W_HIGH", "1W_LOW"), "1M": ("1M_HIGH", "1M_LOW"),
}
POI_ZONE_TYPES = [
    ("RESISTANCE_FLIP", "Resistance Flip"),
    ("SUPPORT_FLIP", "Support Flip"),
    ("FVG", "Fair Value Gap"),
    ("INVERSE_FVG", "Inverse FVG"),
    ("ORDER_BLOCK", "Order Block"),
]
POI_DEFAULT_STRATEGY_TYPES = {"4H_HIGH", "4H_LOW", "PDH", "PDL"}

TRADING_PANEL_TF_OPTIONS = ["1m", "5m", "15m"]
TRADING_PANEL_DAY_PRESETS = ["1", "3", "5", "7", "14", "30", "90"]
TRADING_PANEL_PERIOD_MAP = {
    "1m": {"type": "minute", "span": 1},
    "5m": {"type": "minute", "span": 5},
    "15m": {"type": "minute", "span": 15},
}

# Stable DOM id for the KLineChart instance. Must match the id used by
# ui/components/trading_panel_chart.py and the window.QT19_CHARTS registry
# key set in ui/components/kline_chart.py's onReady handler.
TRADING_PANEL_CHART_ID = "qt19-trading-panel-kline"

SHELL_STATE_CLASS = ShellScreen
