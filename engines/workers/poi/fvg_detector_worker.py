"""File 03.1 Fair Value Gap detector with selectable zone source timeframes.

PATH: engines/workers/poi/fvg_detector_worker.py (REPLACE ENTIRE FILE)

FIX (CRITICAL - "chart turns solid blue and app crashes/restarts") - REAL
root cause found: `self.mdm.get_historical_candles(self.symbol, tf, LOOKBACK_CANDLES)`
passed LOOKBACK_CANDLES (=60) as the `days` argument, not a candle count -
that method's signature is `(symbol, tf, days)`. On "1m" or "15m" source
timeframes (both default ON), this fetched 60 DAYS of the finest-
granularity candles (tens of thousands of rows) and scanned EVERY 3-candle
window in that entire range for FVGs - producing potentially thousands of
overlapping zone overlays. Each is a semi-transparent filled rectangle;
stacking thousands of them compounds into a solid color (exactly the
solid blue seen), the sheer number of chart.createOverlay() calls and the
POI payload sent over the websocket every 3s degrades performance
progressively ("lightens up after some time"), and eventually the
browser/app becomes unresponsive and restarts.

Fixed with two independent safeguards:
  1. Fetch a per-timeframe-appropriate number of DAYS (not a hardcoded 60
     regardless of TF) - just enough to comfortably cover LOOKBACK_CANDLES
     actual candles for that specific timeframe.
  2. Slice the returned candle list down to the last LOOKBACK_CANDLES
     entries in Python BEFORE scanning, regardless of how many the
     Monitor actually returned - this is the real hard cap that
     guarantees at most a few dozen FVG zones ever exist per symbol/TF,
     no matter what get_historical_candles' exact day-to-candle
     conversion does.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType, ZONE_SOURCE_TFS

logger = logging.getLogger("poi_monitor.fvg_detector_worker")

LOOKBACK_CANDLES = 60
LEGACY_SCAN_TFS = ("4H", "1D", "1W", "1M")

# Days to FETCH per timeframe - just enough to comfortably contain
# LOOKBACK_CANDLES actual candles; the real cap is the slice below, this
# is only to avoid over-fetching.
_FETCH_DAYS_FOR_TF: Dict[str, int] = {
    "1m": 1, "5m": 1, "15m": 2, "1H": 4, "4H": 12, "1D": 70, "1W": 450, "1M": 1900,
}


class FVGDetectorWorker:
    """Detect classic three-candle FVGs from selected monitor candle series."""

    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        on_poi_update: Callable[[str, List[POI]], None],
        *,
        zone_source_tf_enabled: Optional[Dict[str, bool]] = None,
        display_enabled: Optional[Dict[str, bool]] = None,
        strategy_enabled: Optional[Dict[str, bool]] = None,
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.on_poi_update = on_poi_update
        self._legacy_source_mode = zone_source_tf_enabled is None
        self.zone_source_tf_enabled = zone_source_tf_enabled or {}
        self.display_enabled = display_enabled or {}
        self.strategy_enabled = strategy_enabled or enabled_types
        self._pois: Dict[str, POI] = {}

    def _selected_source_tfs(self) -> List[str]:
        if self._legacy_source_mode:
            return list(LEGACY_SCAN_TFS)
        return [tf for tf in ZONE_SOURCE_TFS if self.zone_source_tf_enabled.get(tf, False)]

    def _scan_tf(self, tf: str) -> List[POI]:
        days = _FETCH_DAYS_FOR_TF.get(tf, 5)
        candles = self.mdm.get_historical_candles(self.symbol, tf, days)
        if not candles or len(candles) < 3:
            return []
        # Hard cap: only ever scan the most recent LOOKBACK_CANDLES
        # candles, no matter how many were actually returned.
        candles = candles[-LOOKBACK_CANDLES:]
        found: List[POI] = []
        for index in range(2, len(candles)):
            first, third = candles[index - 2], candles[index]
            first_high, first_low = cf(first, "high"), cf(first, "low")
            third_high, third_low = cf(third, "high"), cf(third, "low")
            source_ts = getattr(third, "open_time", third.get("open_time", third.get("bucket_start_ms", 0)) if isinstance(third, dict) else 0)
            common = {
                "symbol": self.symbol,
                "poi_type": POIType.FVG,
                "source_tf": tf,
                "formed_at_index": index,
                "formed_at_ts": float(source_ts),
                "display_enabled": self.display_enabled.get(POIType.FVG, tf in ("1m", "15m")),
                "strategy_enabled": self.strategy_enabled.get(POIType.FVG, False),
            }
            if third_low > first_high:
                found.append(POI(
                    poi_id=f"{self.symbol}:FVG:{tf}:{index}:bull", role="support",
                    price_high=third_low, price_low=first_high,
                    metadata={"direction": "bullish", "impulse_candle_index": index - 1, "source_tf": tf, "broker_boundary": "UTC"},
                    **common,
                ))
            if third_high < first_low:
                found.append(POI(
                    poi_id=f"{self.symbol}:FVG:{tf}:{index}:bear", role="resistance",
                    price_high=first_low, price_low=third_high,
                    metadata={"direction": "bearish", "impulse_candle_index": index - 1, "source_tf": tf, "broker_boundary": "UTC"},
                    **common,
                ))
        return found

    def recompute(self) -> List[POI]:
        wanted = (
            self.strategy_enabled.get(POIType.FVG, self.enabled_types.get(POIType.FVG, False))
            or self.display_enabled.get(POIType.FVG, False)
        )
        if not wanted:
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []
        pois: List[POI] = []
        for tf in self._selected_source_tfs():
            try:
                pois.extend(self._scan_tf(tf))
            except Exception:  # noqa: BLE001
                logger.exception("fvg_scan_failed symbol=%s timeframe=%s", self.symbol, tf)
        self._pois = {poi.poi_id: poi for poi in pois}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.FVG] = bool(enabled)
        self.strategy_enabled[POIType.FVG] = bool(enabled)
        self.recompute()

    def set_source_tf_enabled(self, timeframe: str, enabled: bool) -> None:
        if timeframe not in ZONE_SOURCE_TFS:
            raise ValueError(f"Unsupported zone source timeframe: {timeframe}")
        if self._legacy_source_mode:
            self._legacy_source_mode = False
            self.zone_source_tf_enabled = {tf: tf in LEGACY_SCAN_TFS for tf in ZONE_SOURCE_TFS}
        self.zone_source_tf_enabled[timeframe] = bool(enabled)
        self.recompute()

    async def run_forever(self, poll_seconds: float = 60.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("fvg_detector_worker_failed symbol=%s", self.symbol)
            await asyncio.sleep(poll_seconds)
