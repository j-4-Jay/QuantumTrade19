"""File 03.1 Order Block detector with selectable zone source timeframes."""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType, ZONE_SOURCE_TFS

logger = logging.getLogger("poi_monitor.orderblock_detector_worker")

LOOKBACK_CANDLES = 60
ATR_WINDOW = 14
IMPULSE_MULTIPLIER = 1.8
LEGACY_SCAN_TFS = ("4H", "1D", "1W", "1M")


def _true_range(candle, previous_close: float) -> float:
    high, low = cf(candle, "high"), cf(candle, "low")
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def _rolling_atr(candles: List, index: int, window: int = ATR_WINDOW) -> float:
    start = max(1, index - window)
    ranges = [_true_range(candles[row], cf(candles[row - 1], "close")) for row in range(start, index + 1)]
    return sum(ranges) / len(ranges) if ranges else 0.0


def _is_green(candle) -> bool:
    return cf(candle, "close") > cf(candle, "open")


class OrderBlockDetectorWorker:
    """Detect order blocks from selected local Monitor candle timeframes."""

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
        candles = self.mdm.get_historical_candles(self.symbol, tf, LOOKBACK_CANDLES)
        if not candles or len(candles) < ATR_WINDOW + 2:
            return []
        found: List[POI] = []
        for index in range(2, len(candles)):
            impulse = candles[index]
            atr = _rolling_atr(candles, index - 1)
            impulse_range = cf(impulse, "high") - cf(impulse, "low")
            if atr <= 0 or impulse_range < atr * IMPULSE_MULTIPLIER:
                continue
            previous = candles[index - 1]
            previous_high, previous_low = cf(previous, "high"), cf(previous, "low")
            source_ts = getattr(previous, "open_time", previous.get("open_time", previous.get("bucket_start_ms", 0)) if isinstance(previous, dict) else 0)
            if _is_green(impulse) and not _is_green(previous):
                role, suffix = "support", "bull"
            elif not _is_green(impulse) and _is_green(previous):
                role, suffix = "resistance", "bear"
            else:
                continue
            found.append(POI(
                poi_id=f"{self.symbol}:OB:{tf}:{index}:{suffix}", symbol=self.symbol,
                poi_type=POIType.ORDER_BLOCK, role=role, source_tf=tf,
                price_high=previous_high, price_low=previous_low,
                formed_at_index=index - 1, formed_at_ts=float(source_ts),
                display_enabled=self.display_enabled.get(POIType.ORDER_BLOCK, tf in ("1m", "15m")),
                strategy_enabled=self.strategy_enabled.get(POIType.ORDER_BLOCK, False),
                metadata={"impulse_index": index, "atr": atr, "range": impulse_range, "source_tf": tf, "broker_boundary": "UTC"},
            ))
        return found

    def recompute(self) -> List[POI]:
        if not self.strategy_enabled.get(POIType.ORDER_BLOCK, self.enabled_types.get(POIType.ORDER_BLOCK, False)):
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []
        pois: List[POI] = []
        for tf in self._selected_source_tfs():
            try:
                pois.extend(self._scan_tf(tf))
            except Exception:  # noqa: BLE001
                logger.exception("order_block_scan_failed symbol=%s timeframe=%s", self.symbol, tf)
        self._pois = {poi.poi_id: poi for poi in pois}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.ORDER_BLOCK] = bool(enabled)
        self.strategy_enabled[POIType.ORDER_BLOCK] = bool(enabled)
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
                logger.exception("orderblock_detector_worker_failed symbol=%s", self.symbol)
            await asyncio.sleep(poll_seconds)
