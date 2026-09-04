"""Broker-specific symbol name translation for historical candle requests.

PATH: engines/workers/market_data/broker_symbol_map.py (NEW FILE)

FIX v0.4.38 - "Gold never downloads" root cause, confirmed via direct
broker testing (Diagnose_Gold_v2.py):

    B-XAU_USDT   -> broker candles endpoint returns [] (empty) always
    B-XAUT_USDT  -> broker candles endpoint returns real gold-price data

CoinDCX's public historical-candles REST endpoint uses a DIFFERENT symbol
string for Gold than the live WebSocket ticker feed does. B-XAU_USDT is
correct and must stay unchanged everywhere else in the app (SQLite storage
key, symbol registry, UI labels, WS subscription) - only the outgoing HTTP
request to the broker's /market_data/candles/ endpoint needs the
translated name.

This tiny module is the single source of truth for that translation, so
every worker that calls the candles endpoint (deep_history_downloader_worker.py,
history_depth_prober_worker.py, and historical_data_loader_worker.py if it
also calls this same endpoint directly) uses the exact same mapping and
never drifts out of sync with each other.
"""
from __future__ import annotations

# Internal QT19 symbol -> real broker symbol used ONLY for the
# /market_data/candles/ REST endpoint's "pair" parameter.
CANDLES_SYMBOL_OVERRIDES: dict[str, str] = {
    "B-XAU_USDT": "B-XAUT_USDT",
}


def to_broker_candles_symbol(symbol: str) -> str:
    """Translates an internal QT19 symbol into whatever string the broker's
    candles REST endpoint actually expects. Falls back to the symbol
    unchanged for every pair that doesn't need translation (BTC, ETH, etc.)."""
    return CANDLES_SYMBOL_OVERRIDES.get(symbol, symbol)
