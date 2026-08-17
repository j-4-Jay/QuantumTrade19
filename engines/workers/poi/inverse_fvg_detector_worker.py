"""
engines/workers/poi/inverse_fvg_detector_worker.py

Tier 1 Worker #4 of File 03. Per 123Bull/123Bear Section 5, flips an FVG's
role once price has closed through it a second time in the opposite
direction. Consumes FVG_Detector_Worker's live output directly.

FIX: candle field access now goes through cf() -- see candle_access.py.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIType

logger = logging.getLogger("poi_monitor.inverse_fvg_detector_worker")


class InverseFVGDetectorWorker:
    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        get_fvg_pois: Callable[[], List[POI]],
        on_poi_update: Callable[[str, List[POI]], None],
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.get_fvg_pois = get_fvg_pois
        self.on_poi_update = on_poi_update
        self._pois: Dict[str, POI] = {}
        self._first_close_through: Dict[str, str] = {}  # poi_id -> direction of 1st breach

    def _latest_close(self, tf: str) -> Optional[float]:
        live = self.mdm.get_live_candle(self.symbol, tf)
        if live is not None:
            try:
                return cf(live, "close")
            except (KeyError, AttributeError):
                pass
        hist = self.mdm.get_historical_candles(self.symbol, tf, 2)
        return cf(hist[-1], "close") if hist else None

    def recompute(self) -> List[POI]:
        if not self.enabled_types.get(POIType.INVERSE_FVG, False):
            self._pois = {}
            self.on_poi_update(self.symbol, [])
            return []

        flipped: List[POI] = []
        for fvg in self.get_fvg_pois():
            if fvg.symbol != self.symbol or not fvg.is_range():
                continue
            close = self._latest_close(fvg.source_tf)
            if close is None:
                continue

            closed_above = close > fvg.price_high
            closed_below = close < fvg.price_low
            if not (closed_above or closed_below):
                continue

            direction = "up" if closed_above else "down"
            prior = self._first_close_through.get(fvg.poi_id)

            if prior is None:
                self._first_close_through[fvg.poi_id] = direction
                continue  # first close-through only invalidates the FVG, doesn't flip it yet

            if prior != direction:
                # second close-through, opposite direction -> flip confirmed
                new_role = "support" if fvg.role == "resistance" else "resistance"
                flipped.append(POI(
                    poi_id=f"{fvg.poi_id}:inverse",
                    symbol=self.symbol, poi_type=POIType.INVERSE_FVG, role=new_role,
                    source_tf=fvg.source_tf, price_high=fvg.price_high, price_low=fvg.price_low,
                    formed_at_index=fvg.formed_at_index, formed_at_ts=time.time(),
                    metadata={"original_fvg_id": fvg.poi_id, "original_role": fvg.role},
                ))

        self._pois = {p.poi_id: p for p in flipped}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_types[POIType.INVERSE_FVG] = enabled
        self.recompute()

    async def run_forever(self, poll_seconds: float = 60.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("InverseFVG_Detector_Worker failed for %s", self.symbol)
            await asyncio.sleep(poll_seconds)
