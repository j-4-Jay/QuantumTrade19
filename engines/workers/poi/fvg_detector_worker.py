"""
engines/workers/poi/fvg_detector_worker.py

Tier 1 Worker #2 of File 03. Scans HTF candles for a classic 3-candle Fair
Value Gap and records it as a price-range POI.

FIX: candle field access now goes through cf() -- see candle_access.py.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType

logger = logging.getLogger("poi_monitor.fvg_detector_worker")

SCAN_TFS = ["4H", "1D", "1W", "1M"]
LOOKBACK_CANDLES = 60


class FVGDetectorWorker:
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
        if not candles or len(candles) < 3:
            return []
        found: List[POI] = []
        for i in range(2, len(candles)):
            c1, c2, c3 = candles[i - 2], candles[i - 1], candles[i]
            c1_high, c1_low = cf(c1, "high"), cf(c1, "low")
            c3_high, c3_low = cf(c3, "high"), cf(c3, "low")

            # Bullish FVG: gap up, c3.low sits above c1.high, acts as support on retest.
            if c3_low > c1_high:
                found.append(POI(
                    poi_id=f"{self.symbol}:FVG:{tf}:{i}:bull",
                    symbol=self.symbol, poi_type=POIType.FVG, role="support",
                    source_tf=tf, price_high=c3_low, price_low=c1_high,
                    formed_at_index=i, formed_at_ts=time.time(),
                    metadata={"direction": "bullish", "impulse_candle_index": i - 1},
                ))

            # Bearish FVG: gap down, c3.high sits below c1.low, acts as resistance on retest.
            if c3_high < c1_low:
                found.append(POI(
                    poi_id=f"{self.symbol}:FVG:{tf}:{i}:bear",
                    symbol=self.symbol, poi_type=POIType.FVG, role="resistance",
                    source_tf=tf, price_high=c1_low, price_low=c3_high,
                    formed_at_index=i, formed_at_ts=time.time(),
                    metadata={"direction": "bearish", "impulse_candle_index": i - 1},
                ))
        return found

    def recompute(self) -> List[POI]:
        if not self.enabled_types.get(POIType.FVG, False):
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []
        pois: List[POI] = []
        for tf in SCAN_TFS:
            try:
                pois.extend(self._scan_tf(tf))
            except Exception:  # noqa: BLE001
                logger.exception("FVG scan failed for %s/%s", self.symbol, tf)
        self._pois = {p.poi_id: p for p in pois}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.FVG] = enabled
        self.recompute()

    async def run_forever(self, poll_seconds: float = 60.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("FVG_Detector_Worker failed for %s", self.symbol)
            await asyncio.sleep(poll_seconds)
