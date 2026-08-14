"""
FULL PATH: engines/workers/market_data/tick_normalizer_worker.py (REPLACE ENTIRE FILE)

FIX: from_ws_payload now matches the REAL aggregated-channel field names
confirmed live ("ls" = last price, "mp" = mark price -- not "p"/"price").
Falls back through both old and new field names so nothing else breaks.
"""
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

_WS_PRICE_FIELDS = ("ls", "mp", "p", "price", "last_price", "close", "c")


@dataclass(frozen=True)
class NormalizedTick:
    symbol: str
    price: float
    volume: float
    exchange_ts: int
    received_ts: int
    source: str


class TickNormalizerWorker:
    @staticmethod
    def from_ws_payload(symbol, payload):
        try:
            price = None
            for field in _WS_PRICE_FIELDS:
                if field in payload and payload[field] not in (None, ""):
                    price = float(payload[field])
                    break
            if price is None:
                return None
            volume = float(payload.get("v", payload.get("volume", 0.0)) or 0.0)
            exch_ts = int(payload.get("ctRT", payload.get("T", payload.get("timestamp", time.time() * 1000))))
        except (KeyError, TypeError, ValueError):
            return None
        return NormalizedTick(symbol=symbol, price=price, volume=volume,
                               exchange_ts=exch_ts, received_ts=int(time.time() * 1000), source="ws")

    @staticmethod
    def from_rest_ticker(symbol, payload):
        try:
            price = float(payload["last_price"])
            volume = float(payload.get("volume", 0.0) or 0.0)
            exch_ts = int(payload.get("timestamp", time.time() * 1000))
        except (KeyError, TypeError, ValueError):
            return None
        return NormalizedTick(symbol=symbol, price=price, volume=volume,
                               exchange_ts=exch_ts, received_ts=int(time.time() * 1000), source="rest_fallback")

    @staticmethod
    def from_historical_candle(symbol, candle_close, candle_volume, close_time_ms):
        return NormalizedTick(symbol=symbol, price=candle_close, volume=candle_volume,
                               exchange_ts=close_time_ms, received_ts=close_time_ms, source="historical_backfill")

    @staticmethod
    def is_valid(tick):
        if tick is None:
            return False
        return tick.price > 0 and tick.exchange_ts > 0 and bool(tick.symbol)
