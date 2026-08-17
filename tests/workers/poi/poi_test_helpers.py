"""
FULL PATH: tests/workers/poi/poi_test_helpers.py (NEW FILE)

Shared deterministic test doubles/builders for File 03 POI Worker tests.
These are test-only fixtures: no network calls, no application state, no
CoinDCX dependency. They deliberately return dict-shaped candles so every
POI Worker is verified against the same mocked shape used by the existing
check-gate suite; candle_access.cf() simultaneously preserves production
compatibility with File 02's real Candle dataclass.
"""
from __future__ import annotations

from typing import Dict, Iterable, List


SCAN_TFS = ("1H", "4H", "1D", "1W", "1M")
DETECTOR_SCAN_TFS = ("4H", "1D", "1W", "1M")


def candle(open_: float, high: float, low: float, close: float) -> dict:
    """Return a minimal dict candle matching the File 03 Worker contract."""
    return {"open": open_, "high": high, "low": low, "close": close, "volume": 1.0}


def flat_candles(count: int, start: float = 100.0, span: float = 1.0) -> List[dict]:
    """Stable small-range candles; intentionally cannot meet a 1.8x ATR
    impulse threshold unless a test explicitly appends an impulse candle."""
    rows: List[dict] = []
    for i in range(count):
        base = start + (i % 2) * 0.1
        rows.append(candle(base, base + span, base - span, base + 0.05))
    return rows


class FakeMarketDataMonitor:
    """Duck-type implementation of the documented File 02 public interface.
    Tests can set distinct historical series and live candles per TF."""

    def __init__(self) -> None:
        self.series: Dict[str, List[dict]] = {tf: [] for tf in SCAN_TFS}
        self.live: Dict[str, dict] = {}
        self.fetch_calls: List[tuple[str, str, int]] = []

    def set_series(self, tf: str, rows: Iterable[dict]) -> None:
        self.series[tf] = list(rows)

    def set_live(self, tf: str, row: dict) -> None:
        self.live[tf] = row

    def get_historical_candles(self, symbol: str, tf: str, days: int) -> List[dict]:
        self.fetch_calls.append((symbol, tf, days))
        return list(self.series.get(tf, []))

    def get_live_candle(self, symbol: str, tf: str):
        return self.live.get(tf)

    def subscribe(self, symbol: str) -> None:
        return None

    def get_health(self) -> str:
        return "OK"


class FakeSymbolRegistry:
    """Two-symbol registry proving Tier 2 fan-out/isolation behavior."""

    def __init__(self, symbols: Iterable[str] = ("B-BTC_USDT", "B-ETH_USDT"), tick_size: float = 0.1) -> None:
        self._symbols = list(symbols)
        self._tick_size = tick_size

    def get_active_symbols(self) -> List[str]:
        return list(self._symbols)

    def get_tick_size(self, symbol: str) -> float:
        if symbol not in self._symbols:
            raise KeyError(symbol)
        return self._tick_size
