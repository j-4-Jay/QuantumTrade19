"""FULL PATH: state/app_state_mixins/candle_popup_mixin.py
FT-H.39 Candle info popup: the server side (two actions).
Spec: docs/specs/File_Candle_Info_Popup_Spec_v0.1.0.md

  action "db"      read ONE closed candle from data/historical_candles.db (read-only)
  action "compare" fetch ONE candle from the CoinDCX public candle feed (6 second timeout)

The answer goes back to the browser with window.QT19CandlePopup.receive(chartId, popupId, payload).
It never writes to the database, never places orders and never touches broker credentials.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

import reflex as rx

from engines.workers.market_data.candle_store_worker import DB_PATH
from state.app_state_mixins.shared import TRADING_PANEL_CHART_ID

logger = logging.getLogger(__name__)

STEP_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
FEED_TIMEOUT_S = 6


def _as_dict(open_, high, low, close, volume) -> dict:
    return {"open": float(open_), "high": float(high), "low": float(low), "close": float(close), "volume": float(volume)}


def read_db_candle(symbol: str, timeframe: str, open_time_ms: int, db_path=DB_PATH) -> dict | None:
    """One saved candle, or None when there is no row (for example a candle that is still forming)."""
    path = Path(db_path)
    if not path.exists():
        return None
    con = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True, timeout=5)
    try:
        row = con.execute(
            "SELECT open, high, low, close, volume FROM candles WHERE symbol = ? AND timeframe = ? AND open_time = ?",
            (symbol, timeframe, int(open_time_ms)),
        ).fetchone()
    finally:
        con.close()
    return None if row is None else _as_dict(*row)


def fetch_exchange_candle(symbol: str, timeframe: str, open_time_ms: int) -> dict | None:
    """One candle from the CoinDCX public feed, or None when the feed has no such candle."""
    import requests

    from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker

    def short_get(url, **kwargs):
        kwargs["timeout"] = FEED_TIMEOUT_S
        return requests.get(url, **kwargs)

    step = STEP_MS.get(timeframe, 60_000)
    loader = HistoricalDataLoaderWorker(http_get=short_get, rate_limit_sleep_s=0.0)
    for c in loader.fetch_range(symbol, timeframe, int(open_time_ms) - step, int(open_time_ms) + 2 * step):
        if int(c.open_time) == int(open_time_ms):
            return _as_dict(c.open, c.high, c.low, c.close, c.volume)
    return None


class CandlePopupMixin(rx.State, mixin=True):
    # Register the method as a Reflex state event, matching the existing mixins.
    async def candle_popup_request(self, action: str, popup_id: int, ts: float, symbol: str, tf: str):
        if action not in ("db", "compare"):
            return
        payload = {"kind": action, "candle": None}
        try:
            fn = read_db_candle if action == "db" else fetch_exchange_candle
            payload["candle"] = await asyncio.wait_for(asyncio.to_thread(fn, str(symbol), str(tf), int(ts)), timeout=8)
        except Exception:
            logger.exception("candle_popup_request_failed action=%s", action)
            payload["error"] = "request failed"
        return rx.call_script(
            "window.QT19CandlePopup&&window.QT19CandlePopup.receive(%s,%d,%s)"
            % (json.dumps(TRADING_PANEL_CHART_ID), int(popup_id), json.dumps(payload))
        )
