"""
engines/workers/poi/poi_state_tracker_worker.py

Tier 1 Worker #5 of File 03. Per-POI Approaching/Hit/Crossed/Retesting
state machine, fully independent per poi_id.

FIX: candle field access now goes through cf() -- see candle_access.py.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import MarketDataMonitorLike
from .poi_types import POI, POIState, POIStateRecord

logger = logging.getLogger("poi_monitor.poi_state_tracker_worker")

TOUCH_EPSILON_TICKS = 1.0     # within this many ticks counts as a touch
RETEST_PROXIMITY_TICKS = 3.0  # within this many ticks after crossing counts as a retest


class POIStateTrackerWorker:
    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        tick_size: float,
        get_active_pois: Callable[[], List[POI]],
        on_state_update: Callable[[str, Dict[str, POIStateRecord]], None],
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.tick_size = tick_size
        self.get_active_pois = get_active_pois
        self.on_state_update = on_state_update
        self._states: Dict[str, POIStateRecord] = {}

    def _distance_ticks(self, poi: POI, price: float) -> float:
        if poi.is_range():
            if poi.price_low <= price <= poi.price_high:
                return 0.0
            edge = poi.price_low if price < poi.price_low else poi.price_high
            return abs(price - edge) / self.tick_size
        return abs(price - poi.price) / self.tick_size

    def _side(self, poi: POI, price: float) -> str:
        level = poi.mid_price()
        return "above" if price > level else "below"

    def update_one(self, poi: POI, price: float, now: float) -> POIStateRecord:
        prev = self._states.get(poi.poi_id)
        distance = self._distance_ticks(poi, price)
        touching = distance <= TOUCH_EPSILON_TICKS

        if prev is None:
            state = POIState.HIT if touching else POIState.APPROACHING
            last_touch = now if touching else None
            crossed_dir = None
        else:
            state = prev.state
            last_touch = prev.last_touch_ts
            crossed_dir = prev.crossed_direction
            prev_side = "above" if prev.last_price > poi.mid_price() else "below"
            cur_side = self._side(poi, price)

            if touching:
                last_touch = now
                if state == POIState.CROSSED:
                    state = POIState.RETESTING
                else:
                    state = POIState.HIT
            elif state in (POIState.HIT, POIState.RETESTING) and prev_side != cur_side:
                state = POIState.CROSSED
                crossed_dir = cur_side
            elif state == POIState.CROSSED and distance <= RETEST_PROXIMITY_TICKS:
                state = POIState.RETESTING
                last_touch = now
            elif state not in (POIState.CROSSED, POIState.RETESTING):
                state = POIState.APPROACHING

        record = POIStateRecord(
            poi_id=poi.poi_id, symbol=self.symbol, distance_ticks=distance,
            state=state, last_touch_ts=last_touch, last_price=price,
            crossed_direction=crossed_dir, updated_at=now,
        )
        self._states[poi.poi_id] = record
        return record

    def recompute(self, current_price: Optional[float] = None) -> Dict[str, POIStateRecord]:
        active_pois = self.get_active_pois()
        active_ids = {p.poi_id for p in active_pois}
        self._states = {k: v for k, v in self._states.items() if k in active_ids}

        if current_price is None:
            live = self.mdm.get_live_candle(self.symbol, "1H")
            current_price = cf(live, "close") if live is not None else None
        if current_price is None:
            return self._states

        now = time.time()
        for poi in active_pois:
            self.update_one(poi, current_price, now)

        self.on_state_update(self.symbol, dict(self._states))
        return dict(self._states)

    async def run_forever(self, poll_seconds: float = 5.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("POI_State_Tracker_Worker failed for %s", self.symbol)
            await asyncio.sleep(poll_seconds)
