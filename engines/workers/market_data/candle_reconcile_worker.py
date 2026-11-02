"""
FULL PATH: engines/workers/market_data/candle_reconcile_worker.py
File 02 - Market Data Monitor - candle truth (thread 007)

Background thread. For every active symbol it asks the exchange for the
latest candles (1m about every 10 s, 5m and 15m about every 30 s), one fetch
at a time, and hands them to `apply` (CandleBuilderWorker.apply_exchange_candles)
so software candles match the CoinDCX Futures chart. Backs off on failure.
It never places orders and never touches broker credentials.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("market_data.reconcile")

PERIOD_MS: Dict[str, int] = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
DEFAULT_INTERVAL_S: Dict[str, float] = {"1m": 10.0, "5m": 30.0, "15m": 30.0}
WINDOW_CANDLES: Dict[str, int] = {"1m": 10, "5m": 8, "15m": 4}
MAX_BACKOFF_S = 300.0
MAX_BACKOFF_S = 300.0
SETTLE_OFFSETS_S = (1.5, 4.0, 8.0)


class CandleReconcileWorker:
    def __init__(
        self,
        fetch_range: Callable[[str, str, int, int], list],
        apply: Callable[[str, str, list, int], list],
        get_symbols: Callable[[], List[str]],
        intervals: Optional[Dict[str, float]] = None,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self._fetch_range = fetch_range
        self._apply = apply
        self._get_symbols = get_symbols
        self._intervals = dict(intervals or DEFAULT_INTERVAL_S)
        self._time_fn = time_fn or time.time
        self._due: Dict[Tuple[str, str], float] = {}
        self._fails: Dict[Tuple[str, str], int] = {}
        self._settle_done: set = set()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="CandleReconcile", daemon=True)
        self._thread.start()
        logger.info("candle_reconcile_started intervals=%s", self._intervals)

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        logger.info("candle_reconcile_stopped")

    def run_once(self, now_s: Optional[float] = None) -> int:
        """Runs at most ONE exchange fetch (the most overdue one). Returns 1 if a fetch ran, else 0."""
        now = self._time_fn() if now_s is None else now_s
        symbols = list(self._get_symbols())
        for symbol in symbols:
            for tf in self._intervals:
                self._due.setdefault((symbol, tf), now)
        waiting = [(due, key, None) for key, due in self._due.items() if due <= now and key[0] in symbols]
        waiting.extend(self._settle_candidates(symbols, now))
        if not waiting:
            return 0
        waiting.sort(key=lambda item: item[0])
        _, key, marker = waiting[0]
        if marker is not None:
            self._settle_done.add(marker)
        self._reconcile(key, now)
        return 1

    def _settle_candidates(self, symbols, now):
        """Extra fetches 1.5 s, 4 s and 8 s after every candle close: the exchange can still
        change a closed candle for about 7 s (measured 01-11-2026)."""
        now_ms = int(now * 1000)
        out = []
        for symbol in symbols:
            for tf in self._intervals:
                period = PERIOD_MS[tf]
                boundary = (now_ms // period) * period
                for offset in SETTLE_OFFSETS_S:
                    at_ms = boundary + int(offset * 1000)
                    marker = (symbol, tf, boundary, offset)
                    if at_ms <= now_ms < at_ms + 5_000 and marker not in self._settle_done:
                        out.append((at_ms / 1000.0, (symbol, tf), marker))
        self._settle_done = {m for m in self._settle_done if m[2] >= now_ms - 2 * 900_000}
        return out

    def _reconcile(self, key: Tuple[str, str], now: float) -> None:
        symbol, tf = key
        period = PERIOD_MS[tf]
        now_ms = int(now * 1000)
        start_ms = ((now_ms - WINDOW_CANDLES[tf] * period) // period) * period
        interval = self._intervals[tf]
        try:
            candles = self._fetch_range(symbol, tf, start_ms, now_ms)
            if not candles:
                logger.warning("candle_reconcile_empty symbol=%s timeframe=%s", symbol, tf)
            else:
                corrected = self._apply(symbol, tf, candles, now_ms)
                for c in corrected or []:
                    logger.info(
                        "candle_corrected symbol=%s timeframe=%s open_time=%d o=%s h=%s l=%s c=%s",
                        symbol, tf, c.open_time, c.open, c.high, c.low, c.close,
                    )
            self._fails[key] = 0
            self._due[key] = now + interval
        except Exception as exc:
            count = self._fails.get(key, 0) + 1
            self._fails[key] = count
            delay = min(interval * (2 ** count), MAX_BACKOFF_S)
            self._due[key] = now + delay
            logger.warning(
                "candle_reconcile_failed symbol=%s timeframe=%s failures=%d retry_in_s=%.0f reason=%s: %s",
                symbol, tf, count, delay, type(exc).__name__, exc,
            )

    def _loop(self) -> None:
        while not self._stop.is_set():
            ran = 0
            try:
                ran = self.run_once()
            except Exception:
                logger.exception("candle_reconcile_loop_error")
            self._stop.wait(0.3 if ran else 1.0)
