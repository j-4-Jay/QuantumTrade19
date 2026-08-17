"""
engines/workers/poi/candle_access.py

Tiny compatibility shim, root-fix for "'Candle' object is not subscriptable".

Every File 03 Worker reads OHLC fields off whatever Market_Data_Monitor
hands back. In production that's the REAL Candle dataclass from File 02
(attribute access: c.high, c.close, c.open, c.low, c.volume, c.open_time,
c.close_time). In the mocked check-gate tests it's a plain dict
(c["high"], c["close"], ...) to keep those tests decoupled from File 02's
exact dataclass shape. Every Worker now reads fields through cf() so both
shapes work identically -- this was the missing piece, not a data bug.
"""
from __future__ import annotations

from typing import Any


def cf(candle: Any, field: str):
    """candle-field: works whether `candle` is a dict or an object with
    attributes (e.g. Market_Data_Monitor's real Candle dataclass)."""
    if isinstance(candle, dict):
        return candle[field]
    return getattr(candle, field)
