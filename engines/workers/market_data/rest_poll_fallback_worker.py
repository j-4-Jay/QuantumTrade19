"""
FULL PATH: engines/workers/market_data/rest_poll_fallback_worker.py (REPLACE ENTIRE FILE)

v3: mandatory REST-fallback lifecycle and failure logging. Previous code
silently swallowed every polling error (`except Exception: pass`), making a
long DEGRADED interval impossible to audit. This version logs engagement,
disengagement, first successful tick, periodic success heartbeats, and
failures (rate-limited to avoid log floods while still preserving evidence).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

import requests

FUTURES_PRICES_URL = "https://public.coindcx.com/market_data/v3/current_prices/futures/rt"
DEFAULT_POLL_INTERVAL_S = 1.5
_FAILURE_LOG_MIN_INTERVAL_S = 30.0
_SUCCESS_LOG_INTERVAL_S = 60.0
_PRICE_FIELD_CANDIDATES = ("last_price", "ls", "mp", "price", "close", "c")
_CONTAINER_KEYS = ("prices", "data")

logger = logging.getLogger("market_data.rest_fallback")


class RestPollFallbackWorker:
    def __init__(self, on_tick=None, http_get=None, poll_interval_s: float = DEFAULT_POLL_INTERVAL_S) -> None:
        self._on_tick = on_tick
        self._http_get = http_get or requests.get
        self._poll_interval_s = poll_interval_s
        self._lock = threading.RLock()
        self._active: Dict[str, threading.Event] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._last_ticker_cache: Dict[str, dict] = {}
        self._failure_count: Dict[str, int] = {}
        self._last_failure_log_ts: Dict[str, float] = {}
        self._last_success_log_ts: Dict[str, float] = {}

    def engage(self, symbol: str) -> None:
        with self._lock:
            if symbol in self._active:
                logger.debug("rest_fallback_already_engaged symbol=%s", symbol)
                return
            stop_event = threading.Event()
            self._active[symbol] = stop_event
            self._failure_count[symbol] = 0
            thread = threading.Thread(
                target=self._poll_loop,
                args=(symbol, stop_event),
                name=f"RESTFallback:{symbol}",
                daemon=True,
            )
            self._threads[symbol] = thread
            thread.start()
        logger.warning("rest_fallback_engaged symbol=%s poll_interval_s=%.2f", symbol, self._poll_interval_s)

    def disengage(self, symbol: str) -> None:
        with self._lock:
            stop_event = self._active.pop(symbol, None)
            self._threads.pop(symbol, None)
            self._failure_count.pop(symbol, None)
            self._last_failure_log_ts.pop(symbol, None)
            self._last_success_log_ts.pop(symbol, None)
        if stop_event:
            stop_event.set()
            logger.info("rest_fallback_disengaged symbol=%s", symbol)

    def is_engaged(self, symbol: str) -> bool:
        with self._lock:
            return symbol in self._active

    def _poll_loop(self, symbol: str, stop_event: threading.Event) -> None:
        logger.info("rest_fallback_poll_loop_started symbol=%s", symbol)
        poll_count = 0
        successful_ticks = 0
        while not stop_event.is_set():
            poll_count += 1
            try:
                resp = self._http_get(FUTURES_PRICES_URL, timeout=5)
                resp.raise_for_status()
                payload = resp.json() or {}
                raw_row = self._extract_row_for_symbol(payload, symbol)
                if raw_row is None:
                    self._log_failure(symbol, "symbol_row_missing")
                else:
                    normalized = self._normalize_row(raw_row)
                    if normalized is None:
                        self._log_failure(symbol, "price_normalization_failed")
                    else:
                        with self._lock:
                            self._last_ticker_cache[symbol] = normalized
                            self._failure_count[symbol] = 0
                        successful_ticks += 1
                        self._log_success(symbol, successful_ticks, normalized["last_price"])
                        if self._on_tick:
                            try:
                                self._on_tick(symbol, normalized)
                            except Exception:
                                logger.exception("rest_fallback_on_tick_callback_failed symbol=%s", symbol)
            except Exception as exc:
                self._log_failure(symbol, f"{type(exc).__name__}: {exc}", exc_info=True)

            stop_event.wait(self._poll_interval_s)

        logger.info(
            "rest_fallback_poll_loop_stopped symbol=%s polls=%d successful_ticks=%d",
            symbol, poll_count, successful_ticks,
        )

    def _log_failure(self, symbol: str, reason: str, exc_info: bool = False) -> None:
        now = time.time()
        with self._lock:
            count = self._failure_count.get(symbol, 0) + 1
            self._failure_count[symbol] = count
            last = self._last_failure_log_ts.get(symbol, 0.0)
            should_log = count == 1 or now - last >= _FAILURE_LOG_MIN_INTERVAL_S
            if should_log:
                self._last_failure_log_ts[symbol] = now
        if should_log:
            logger.warning(
                "rest_fallback_poll_failed symbol=%s consecutive_failures=%d reason=%s",
                symbol, count, reason, exc_info=exc_info,
            )

    def _log_success(self, symbol: str, successful_ticks: int, last_price: float) -> None:
        now = time.time()
        with self._lock:
            last = self._last_success_log_ts.get(symbol, 0.0)
            should_log = successful_ticks == 1 or now - last >= _SUCCESS_LOG_INTERVAL_S
            if should_log:
                self._last_success_log_ts[symbol] = now
        if should_log:
            logger.info(
                "rest_fallback_poll_ok symbol=%s successful_ticks=%d last_price=%s",
                symbol, successful_ticks, last_price,
            )

    @staticmethod
    def _extract_row_for_symbol(payload, symbol: str):
        """Real shape: {"ts":..., "vs":..., "prices": {pair: {...}}}."""
        if not isinstance(payload, dict):
            return None
        for key in _CONTAINER_KEYS:
            container = payload.get(key)
            if isinstance(container, dict) and symbol in container:
                return container[symbol]
        return payload.get(symbol)

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
        with self._lock:
            cached = self._last_ticker_cache.get(symbol)
            return dict(cached) if cached else None
