"""
FULL PATH: engines/workers/market_data/rest_poll_fallback_worker.py (REPLACE ENTIRE FILE)

FIX v2: confirmed via live diagnostic that the real response shape from
https://public.coindcx.com/market_data/v3/current_prices/futures/rt is:
    {"ts": ..., "vs": ..., "prices": {"B-BTC_USDT": {...}, "B-ETH_USDT": {...}, ...}}
The pair data lives under the "prices" key -- not "data", not flat at the
top level. Price field inside each pair's row is "ls" (last price).
"""
import threading
from typing import Dict, Optional
import requests

FUTURES_PRICES_URL = "https://public.coindcx.com/market_data/v3/current_prices/futures/rt"
DEFAULT_POLL_INTERVAL_S = 1.5
_PRICE_FIELD_CANDIDATES = ("last_price", "ls", "mp", "price", "close", "c")
_CONTAINER_KEYS = ("prices", "data")


class RestPollFallbackWorker:
    def __init__(self, on_tick=None, http_get=None, poll_interval_s=DEFAULT_POLL_INTERVAL_S):
        self._on_tick = on_tick
        self._http_get = http_get or requests.get
        self._poll_interval_s = poll_interval_s
        self._lock = threading.RLock()
        self._active: Dict[str, threading.Event] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._last_ticker_cache: Dict[str, dict] = {}

    def engage(self, symbol: str) -> None:
        with self._lock:
            if symbol in self._active:
                return
            stop_event = threading.Event()
            self._active[symbol] = stop_event
            t = threading.Thread(target=self._poll_loop, args=(symbol, stop_event), daemon=True)
            self._threads[symbol] = t
            t.start()

    def disengage(self, symbol: str) -> None:
        with self._lock:
            stop_event = self._active.pop(symbol, None)
            if stop_event:
                stop_event.set()

    def is_engaged(self, symbol: str) -> bool:
        with self._lock:
            return symbol in self._active

    def _poll_loop(self, symbol: str, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                resp = self._http_get(FUTURES_PRICES_URL, timeout=5)
                resp.raise_for_status()
                payload = resp.json() or {}
                raw_row = self._extract_row_for_symbol(payload, symbol)
                if raw_row is not None:
                    normalized = self._normalize_row(raw_row)
                    if normalized is not None:
                        self._last_ticker_cache[symbol] = normalized
                        if self._on_tick:
                            self._on_tick(symbol, normalized)
            except Exception:
                pass
            stop_event.wait(self._poll_interval_s)

    @staticmethod
    def _extract_row_for_symbol(payload, symbol: str):
        """Real shape confirmed live: {"ts":..., "vs":..., "prices": {pair: {...}}}."""
        if not isinstance(payload, dict):
            return None
        for key in _CONTAINER_KEYS:
            container = payload.get(key)
            if isinstance(container, dict) and symbol in container:
                return container[symbol]
        if symbol in payload:
            return payload[symbol]
        return None

    @staticmethod
    def _normalize_row(raw_row) -> Optional[dict]:
        if isinstance(raw_row, (int, float, str)):
            try:
                return {"last_price": float(raw_row)}
            except (TypeError, ValueError):
                return None
        if not isinstance(raw_row, dict):
            return None
        for field in _PRICE_FIELD_CANDIDATES:
            if field in raw_row and raw_row[field] not in (None, ""):
                try:
                    price = float(raw_row[field])
                except (TypeError, ValueError):
                    continue
                out = dict(raw_row)
                out["last_price"] = price
                return out
        return None

    def get_last_cached(self, symbol: str) -> Optional[dict]:
        return self._last_ticker_cache.get(symbol)
