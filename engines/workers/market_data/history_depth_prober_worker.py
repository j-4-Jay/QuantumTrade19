"""Broker-only historical depth probe.

TARGET PATH: D:\QuantumTrade19\engines\workers\market_data\history_depth_prober_worker.py
REPLACE THE ENTIRE FILE.

FIX v0.4.38 - Gold broker-ceiling probe also uses the wrong symbol name
for the same reason the downloader did: the broker's candles REST endpoint
needs "B-XAUT_USDT" for Gold, not "B-XAU_USDT". Applied the same
to_broker_candles_symbol() translation (engines/workers/market_data/
broker_symbol_map.py) to the probe's outgoing HTTP request only - the
internal symbol key used for results/caching is completely unchanged.

FIX v0.4.20 (carried forward) - probe timeouts found via real running-app
error logs: increased HTTP timeout from 10s to 20s and added up to 2
retries with backoff, since the probe was failing under real network load
(competing with WS feed, REST fallback, and download threads) even though
the broker itself was reachable and responsive.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import requests

from engines.workers.market_data.broker_symbol_map import to_broker_candles_symbol

logger = logging.getLogger("market_data.history_depth_prober")

CANDLES_URL = "https://public.coindcx.com/market_data/candles/"
MAX_LIMIT_PER_CALL = 1000
PROBE_PACING_S = 0.30
PROBE_TIMEOUT_S = 20
PROBE_MAX_RETRIES = 2
PROBE_RETRY_BACKOFF_S = 2.0
EARLY_START_MS = 1420070400000


class HistoryDepthProberWorker:
    def __init__(
        self,
        manifest=None,
        http_get=None,
        on_progress: Optional[Callable[[str, str, dict], None]] = None,
    ) -> None:
        # manifest remains an accepted optional argument for constructor compatibility.
        # It is intentionally unused: a broker probe must never mutate local metadata.
        self._http_get = http_get or requests.get
        self._on_progress = on_progress
        self._active: dict[tuple[str, str], threading.Event] = {}
        self._results: dict[tuple[str, str], dict] = {}
        self._lock = threading.RLock()

    def start_probe(self, symbol: str, timeframe: str) -> None:
        key = (symbol, timeframe)
        with self._lock:
            if key in self._active:
                return
            stop_event = threading.Event()
            self._active[key] = stop_event
        threading.Thread(
            target=self._probe_loop,
            args=(symbol, timeframe, stop_event),
            daemon=True,
            name=f"QT19DepthProbe-{symbol}-{timeframe}",
        ).start()

    def is_probing(self, symbol: str, timeframe: str) -> bool:
        with self._lock:
            return (symbol, timeframe) in self._active

    def get_ceiling_days(self, symbol: str, timeframe: str) -> Optional[float]:
        with self._lock:
            result = self._results.get((symbol, timeframe))
        return None if result is None else result.get("span_days")

    def get_result(self, symbol: str, timeframe: str) -> dict:
        with self._lock:
            return dict(self._results.get((symbol, timeframe), {}))

    def _emit(self, symbol: str, timeframe: str, payload: dict) -> None:
        if self._on_progress:
            try:
                self._on_progress(symbol, timeframe, payload)
            except Exception:
                logger.exception("history_depth_probe_progress_callback_failed")

    def _request_with_retries(self, symbol: str, timeframe: str, cursor_end: int):
        """Makes one probe HTTP request (using the real broker candles
        symbol via to_broker_candles_symbol()), retrying up to
        PROBE_MAX_RETRIES times on a timeout/connection error before
        giving up."""
        broker_symbol = to_broker_candles_symbol(symbol)
        last_exc: Exception | None = None
        for attempt in range(PROBE_MAX_RETRIES + 1):
            try:
                return self._http_get(
                    CANDLES_URL,
                    params={
                        "pair": broker_symbol,
                        "interval": timeframe,
                        "startTime": EARLY_START_MS,
                        "endTime": cursor_end,
                        "limit": MAX_LIMIT_PER_CALL,
                    },
                    timeout=PROBE_TIMEOUT_S,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                if attempt < PROBE_MAX_RETRIES:
                    logger.warning(
                        "history_depth_probe_retry symbol=%s timeframe=%s attempt=%d error=%s",
                        symbol, timeframe, attempt + 1, exc,
                    )
                    time.sleep(PROBE_RETRY_BACKOFF_S)
                    continue
                raise
        if last_exc:
            raise last_exc
        return None

    def _probe_loop(self, symbol: str, timeframe: str, stop_event: threading.Event) -> None:
        started_end = int(time.time() * 1000)
        cursor_end = started_end
        oldest_ms: int | None = None
        newest_ms: int | None = None
        error: str | None = None

        try:
            while not stop_event.is_set() and cursor_end > EARLY_START_MS:
                response = self._request_with_retries(symbol, timeframe, cursor_end)
                response.raise_for_status()
                rows = response.json() or []
                if not rows:
                    break

                batch_times = [int(row["time"]) for row in rows if "time" in row]
                if not batch_times:
                    break
                batch_oldest = min(batch_times)
                batch_newest = max(batch_times)
                oldest_ms = batch_oldest if oldest_ms is None else min(oldest_ms, batch_oldest)
                newest_ms = batch_newest if newest_ms is None else max(newest_ms, batch_newest)
                span_days = round((newest_ms - oldest_ms) / 86_400_000, 1)
                self._emit(symbol, timeframe, {"probing": True, "span_days_so_far": span_days})

                if batch_oldest >= cursor_end:
                    break
                cursor_end = batch_oldest - 1
                time.sleep(PROBE_PACING_S)
        except Exception as exc:
            error = str(exc)
            logger.exception("history_depth_probe_failed symbol=%s timeframe=%s", symbol, timeframe)
        finally:
            span_days = round((newest_ms - oldest_ms) / 86_400_000, 1) if oldest_ms is not None and newest_ms is not None else 0.0
            result = {
                "span_days": span_days,
                "oldest_open_time": oldest_ms,
                "newest_open_time": newest_ms,
                "error": error,
                "cancelled": stop_event.is_set(),
                "probed_at_ms": int(time.time() * 1000),
            }
            with self._lock:
                self._results[(symbol, timeframe)] = result
                self._active.pop((symbol, timeframe), None)
            self._emit(symbol, timeframe, {"probing": False, "ceiling_days": span_days, "error": error})
