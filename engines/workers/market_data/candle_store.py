"""Passive, event-subscribed candle cache backing Market_Data_Monitor's get_live_candle()/get_historical_candles().
Not a Worker itself -- lets the Monitor serve reads without reaching into a Worker's internals directly.
"""
from __future__ import annotations
import threading
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Tuple
from engines.event_bus.bus import event_bus

MAX_CANDLES_PER_SERIES = 50_000


class CandleStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._series: Dict[Tuple[str, str], Deque[dict]] = defaultdict(lambda: deque(maxlen=MAX_CANDLES_PER_SERIES))
        event_bus.subscribe("market_data.candle.closed", self._on_candle)
        event_bus.subscribe("market_data.history.candle_loaded", self._on_candle)
        event_bus.subscribe("market_data.deep_history.candle_loaded", self._on_candle)

    def _on_candle(self, event: dict) -> None:
        key = (event["symbol"], event["timeframe"])
        with self._lock:
            series = self._series[key]
            if series and series[-1]["bucket_start_ms"] == event.get("bucket_start_ms"):
                series[-1] = event
            else:
                series.append(event)

    def get_live_candle(self, symbol: str, timeframe: str) -> Optional[dict]:
        with self._lock:
            series = self._series.get((symbol, timeframe))
            return dict(series[-1]) if series else None

    def get_historical_candles(self, symbol: str, timeframe: str, days: int) -> List[dict]:
        with self._lock:
            series = self._series.get((symbol, timeframe), deque())
            if not series:
                return []
            cutoff_ms = series[-1]["bucket_start_ms"] - days * 86_400_000
            return [dict(c) for c in series if c["bucket_start_ms"] >= cutoff_ms]
