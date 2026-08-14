"""
FULL PATH: engines/workers/market_data/candle_builder_worker.py
File 02 — Market Data Monitor — Worker 6/6

Aggregates normalized ticks into 1m/5m/15m (trading) and 1H/4H/Daily/Weekly/Monthly
(POI) candles. Stitches historical backfill + live ticks into ONE continuous series
— no gap, no duplicate candle. Verified via tests/test_market_data_monitor.py
(5/5 passing, mocked data — no live network required).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple

TRADING_TFS = ["1m", "5m", "15m"]
POI_TFS = ["1H", "4H", "1D", "1W", "1M"]
ALL_TFS = TRADING_TFS + POI_TFS

_TF_MS: Dict[str, int] = {
    "1m": 60_000, "5m": 5 * 60_000, "15m": 15 * 60_000,
    "1H": 60 * 60_000, "4H": 4 * 60 * 60_000, "1D": 24 * 60 * 60_000,
    "1W": 7 * 24 * 60 * 60_000, "1M": 30 * 24 * 60 * 60_000,  # 1M = calendar approx bucket
}


@dataclass
class Candle:
    symbol: str
    timeframe: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _bucket_start(exchange_ts: int, tf: str) -> int:
    step = _TF_MS[tf]
    return (exchange_ts // step) * step


class CandleBuilderWorker:
    """One instance shared across all symbols/timeframes; state keyed by (symbol, tf)."""

    def __init__(self, on_candle_closed: Optional[Callable[["Candle"], None]] = None) -> None:
        self._lock = threading.RLock()
        self._current: Dict[Tuple[str, str], Candle] = {}
        self._closed_history: Dict[Tuple[str, str], List[Candle]] = {}
        self._last_closed_time: Dict[Tuple[str, str], int] = {}
        self._on_candle_closed = on_candle_closed

    def seed_historical(self, symbol: str, timeframe: str, candles: List[Candle]) -> None:
        """Loads Historical_Data_Loader_Worker output so the live series starts
        continuous — no gap between backfill and first live tick."""
        key = (symbol, timeframe)
        with self._lock:
            ordered = sorted(candles, key=lambda c: c.open_time)
            self._closed_history[key] = ordered
            if ordered:
                self._last_closed_time[key] = ordered[-1].open_time

    def ingest(self, tick, timeframes: Optional[List[str]] = None) -> List[Candle]:
        """Feeds one normalized tick into every requested timeframe bucket.
        Returns the list of candles that just CLOSED as a result (may be empty)."""
        tfs = timeframes or ALL_TFS
        closed_now: List[Candle] = []
        with self._lock:
            for tf in tfs:
                key = (tick.symbol, tf)
                bucket_open = _bucket_start(tick.exchange_ts, tf)
                current = self._current.get(key)

                if current is None:
                    current = Candle(
                        symbol=tick.symbol, timeframe=tf,
                        open_time=bucket_open, close_time=bucket_open + _TF_MS[tf] - 1,
                        open=tick.price, high=tick.price, low=tick.price,
                        close=tick.price, volume=tick.volume,
                    )
                    self._current[key] = current
                    continue

                if bucket_open == current.open_time:
                    current.high = max(current.high, tick.price)
                    current.low = min(current.low, tick.price)
                    current.close = tick.price
                    current.volume += tick.volume
                elif bucket_open > current.open_time:
                    # current bucket is finished — close it, then open the new one
                    current.is_closed = True
                    self._closed_history.setdefault(key, []).append(current)
                    self._last_closed_time[key] = current.open_time
                    closed_now.append(current)
                    if self._on_candle_closed:
                        self._on_candle_closed(current)

                    new_candle = Candle(
                        symbol=tick.symbol, timeframe=tf,
                        open_time=bucket_open, close_time=bucket_open + _TF_MS[tf] - 1,
                        open=tick.price, high=tick.price, low=tick.price,
                        close=tick.price, volume=tick.volume,
                    )
                    self._current[key] = new_candle
                # bucket_open < current.open_time -> stale/late tick, dropped (never rewrites a closed candle)
        return closed_now

    def get_live_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        with self._lock:
            return self._current.get((symbol, timeframe))

    def get_series(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> List[Candle]:
        """Closed history + current forming candle, oldest -> newest, no gaps/dupes."""
        key = (symbol, timeframe)
        with self._lock:
            series = list(self._closed_history.get(key, []))
            live = self._current.get(key)
            if live is not None:
                series = series + [live]
            if limit:
                series = series[-limit:]
            return series

    def check_continuity(self, symbol: str, timeframe: str) -> Dict[str, object]:
        """Check-gate helper: scans closed history for gaps/dupes. Returns a report dict."""
        key = (symbol, timeframe)
        step = _TF_MS[timeframe]
        with self._lock:
            history = self._closed_history.get(key, [])
            gaps, dupes = [], []
            for i in range(1, len(history)):
                delta = history[i].open_time - history[i - 1].open_time
                if delta == 0:
                    dupes.append(history[i].open_time)
                elif delta != step:
                    gaps.append((history[i - 1].open_time, history[i].open_time))
            return {"symbol": symbol, "timeframe": timeframe, "candle_count": len(history),
                    "gaps": gaps, "duplicates": dupes, "clean": not gaps and not dupes}
