"""
engines/workers/poi/orderblock_detector_worker.py

Tier 1 Worker #3 of File 03. Detects the last opposite-colored candle
before a strong impulsive move (ATR-relative threshold) and records it as
a price-range POI.

FIX: candle field access now goes through cf() -- see candle_access.py.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType

logger = logging.getLogger("poi_monitor.orderblock_detector_worker")

SCAN_TFS = ["4H", "1D", "1W", "1M"]
LOOKBACK_CANDLES = 60
ATR_WINDOW = 14
IMPULSE_MULTIPLIER = 1.8  # candle range must exceed ATR * this to count as impulsive


def _true_range(c, prev_close: float) -> float:
    high, low = cf(c, "high"), cf(c, "low")
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _rolling_atr(candles: List, idx: int, window: int = ATR_WINDOW) -> float:
    start = max(1, idx - window)
    trs = [
        _true_range(candles[i], cf(candles[i - 1], "close"))
        for i in range(start, idx + 1)
        if i > 0
    ]
    return sum(trs) / len(trs) if trs else 0.0


def _is_green(c) -> bool:
    return cf(c, "close") > cf(c, "open")


class OrderBlockDetectorWorker:
    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        on_poi_update: Callable[[str, List[POI]], None],
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.on_poi_update = on_poi_update
        self._pois: Dict[str, POI] = {}

    def _scan_tf(self, tf: str) -> List[POI]:
        candles = self.mdm.get_historical_candles(self.symbol, tf, LOOKBACK_CANDLES)
        if not candles or len(candles) < ATR_WINDOW + 2:
            return []

        found: List[POI] = []
        for i in range(2, len(candles)):
            impulse = candles[i]
            atr = _rolling_atr(candles, i - 1)
            impulse_high, impulse_low = cf(impulse, "high"), cf(impulse, "low")
            candle_range = impulse_high - impulse_low
            if atr <= 0 or candle_range < atr * IMPULSE_MULTIPLIER:
                continue

            impulse_up = _is_green(impulse)
            prev = candles[i - 1]
            prev_high, prev_low = cf(prev, "high"), cf(prev, "low")

            if impulse_up and not _is_green(prev):
                # last red candle before a bullish impulse -> bullish OB, support zone
                found.append(POI(
                    poi_id=f"{self.symbol}:OB:{tf}:{i}:bull",
                    symbol=self.symbol, poi_type=POIType.ORDER_BLOCK, role="support",
                    source_tf=tf, price_high=prev_high, price_low=prev_low,
                    formed_at_index=i - 1, formed_at_ts=time.time(),
                    metadata={"impulse_index": i, "atr": atr, "range": candle_range},
                ))
            elif (not impulse_up) and _is_green(prev):
                # last green candle before a bearish impulse -> bearish OB, resistance zone
                found.append(POI(
                    poi_id=f"{self.symbol}:OB:{tf}:{i}:bear",
                    symbol=self.symbol, poi_type=POIType.ORDER_BLOCK, role="resistance",
                    source_tf=tf, price_high=prev_high, price_low=prev_low,
                    formed_at_index=i - 1, formed_at_ts=time.time(),
                    metadata={"impulse_index": i, "atr": atr, "range": candle_range},
                ))
        return found

    def recompute(self) -> List[POI]:
        if not self.enabled_types.get(POIType.ORDER_BLOCK, False):
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []
        pois: List[POI] = []
        for tf in SCAN_TFS:
            try:
                pois.extend(self._scan_tf(tf))
            except Exception:  # noqa: BLE001
                logger.exception("Order Block scan failed for %s/%s", self.symbol, tf)
        self._pois = {p.poi_id: p for p in pois}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.ORDER_BLOCK] = enabled
        self.recompute()

    async def run_forever(self, poll_seconds: float = 60.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("OrderBlock_Detector_Worker failed for %s", self.symbol)
            await asyncio.sleep(poll_seconds)
