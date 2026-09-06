"""File 03.1 Inverse FVG detector preserving source-timeframe metadata.

PATH: engines/workers/poi/inverse_fvg_detector_worker.py (REPLACE ENTIRE FILE)

FIX (Display/Strategy independence) - same fix as the other zone
workers: recompute() now runs whenever EITHER display_enabled OR
strategy_enabled wants Inverse FVG, not only when strategy_enabled is
true.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType, ZONE_SOURCE_TFS

logger = logging.getLogger("poi_monitor.inverse_fvg_detector_worker")

LEGACY_SCAN_TFS = ("4H", "1D", "1W", "1M")


class InverseFVGDetectorWorker:
    """Create inverse FVGs only after opposite-direction second breach."""

    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        get_fvg_pois: Callable[[], List[POI]],
        on_poi_update: Callable[[str, List[POI]], None],
        *,
        zone_source_tf_enabled: Optional[Dict[str, bool]] = None,
        display_enabled: Optional[Dict[str, bool]] = None,
        strategy_enabled: Optional[Dict[str, bool]] = None,
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.get_fvg_pois = get_fvg_pois
        self.on_poi_update = on_poi_update
        self._legacy_source_mode = zone_source_tf_enabled is None
        self.zone_source_tf_enabled = zone_source_tf_enabled or {}
        self.display_enabled = display_enabled or {}
        self.strategy_enabled = strategy_enabled or enabled_types
        self._pois: Dict[str, POI] = {}
        self._first_close_through: Dict[str, str] = {}

    def _source_enabled(self, timeframe: str) -> bool:
        return timeframe in LEGACY_SCAN_TFS if self._legacy_source_mode else self.zone_source_tf_enabled.get(timeframe, False)

    def _latest_close(self, tf: str) -> Optional[float]:
        live = self.mdm.get_live_candle(self.symbol, tf)
        if live is not None:
            try:
                return cf(live, "close")
            except (AttributeError, KeyError):
                pass
        candles = self.mdm.get_historical_candles(self.symbol, tf, 2)
        return cf(candles[-1], "close") if candles else None

    def recompute(self) -> List[POI]:
        wanted = (
            self.strategy_enabled.get(POIType.INVERSE_FVG, self.enabled_types.get(POIType.INVERSE_FVG, False))
            or self.display_enabled.get(POIType.INVERSE_FVG, False)
        )
        if not wanted:
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []
        flipped: List[POI] = []
        active_ids: set[str] = set()
        for fvg in self.get_fvg_pois():
            if fvg.symbol != self.symbol or not fvg.is_range() or not self._source_enabled(fvg.source_tf):
                continue
            active_ids.add(fvg.poi_id)
            close = self._latest_close(fvg.source_tf)
            if close is None:
                continue
            direction = "up" if close > fvg.price_high else "down" if close < fvg.price_low else None
            if direction is None:
                continue
            prior = self._first_close_through.get(fvg.poi_id)
            if prior is None:
                self._first_close_through[fvg.poi_id] = direction
                continue
            if prior == direction:
                continue
            flipped.append(POI(
                poi_id=f"{fvg.poi_id}:inverse", symbol=self.symbol,
                poi_type=POIType.INVERSE_FVG,
                role="support" if fvg.role == "resistance" else "resistance",
                source_tf=fvg.source_tf, price_high=fvg.price_high, price_low=fvg.price_low,
                formed_at_index=fvg.formed_at_index, formed_at_ts=fvg.formed_at_ts,
                display_enabled=self.display_enabled.get(POIType.INVERSE_FVG, fvg.display_enabled),
                strategy_enabled=self.strategy_enabled.get(POIType.INVERSE_FVG, False),
                metadata={"original_fvg_id": fvg.poi_id, "original_role": fvg.role, "source_tf": fvg.source_tf, "broker_boundary": "UTC"},
            ))
        self._first_close_through = {poi_id: direction for poi_id, direction in self._first_close_through.items() if poi_id in active_ids}
        self._pois = {poi.poi_id: poi for poi in flipped}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.INVERSE_FVG] = bool(enabled)
        self.strategy_enabled[POIType.INVERSE_FVG] = bool(enabled)
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
                logger.exception("inverse_fvg_detector_worker_failed symbol=%s", self.symbol)
            await asyncio.sleep(poll_seconds)
