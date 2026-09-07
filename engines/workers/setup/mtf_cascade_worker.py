"""File 04 - Setup Detection Monitor - Worker 7/7: MTF Cascade.
PATH: engines/workers/setup/mtf_cascade_worker.py (REPLACE ENTIRE FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md / 123Bear_Setup_Master_Prompt.md
Section 12 (identical wording, mirrored direction):

  When a setup CONFIRMS on 15m or 5m: do NOT enter yet.
    1. Start watching the 1m chart at the SAME POI/FVG zone for its own
       independent same-direction setup.
    2. Cancel immediately on ANY of:
       a. Timeout: one full length of the trigger candle in 1m candles
          (15 min for a 15m trigger, 6 min for a 5m trigger - both adjustable).
       b. Price leaves the POI/FVG zone's proximity guard distance (adjustable).
       c. Price breaks past the extreme point of the original 5m/15m 3-candle
          setup (its would-be SL) - the original idea is invalidated.
    3. If cancelled for ANY reason: take NO trade at all. Never fall back to
       the wider 5m/15m stop.
    4. If the 1m setup confirms in time, same direction, inside proximity:
       enter using the 1m candles' TIGHTER stop loss.
    5. 15m and 5m triggers both drop straight to 1m - never an intermediate step.

Does not run its own copy of the Candle1/2/3 machine - wires one dedicated
Bull123FSMWorker/Bear123FSMWorker pair scoped to the 1m timeframe (per the
locked instruction to never re-derive that FSM), and only adds the
cascade-specific timeout/proximity/extreme-break bookkeeping around it.

(No logic changes in this revision - only Bull123FSMWorker/Bear123FSMWorker
internals changed. Replace this file only to keep the whole File 04 module
on one consistent revision.)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from engines.workers.setup.setup_types import ConfirmedSetup, SetupDirection

DEFAULT_TIMEOUT_MINUTES = {"15m": 15, "5m": 6}
DEFAULT_PROXIMITY_TICKS = 20


@dataclass
class CascadeWatch:
    watch_id: str
    symbol: str
    trigger_tf: str
    direction: str
    poi_id: str
    zone_low: float
    zone_high: float
    htf_extreme: float
    parent_event_id: str
    deadline_ts: float
    proximity_ticks: float
    tick_size: float
    status: str = "WATCHING"


class MTFCascadeWorker:
    def __init__(
        self,
        bull_1m_fsm,
        bear_1m_fsm,
        timeout_minutes: Optional[Dict[str, int]] = None,
        proximity_ticks: float = DEFAULT_PROXIMITY_TICKS,
    ) -> None:
        self._bull_1m_fsm = bull_1m_fsm
        self._bear_1m_fsm = bear_1m_fsm
        self._timeout_minutes = dict(timeout_minutes or DEFAULT_TIMEOUT_MINUTES)
        self._proximity_ticks = proximity_ticks
        self._watches: Dict[str, CascadeWatch] = {}

    def start_watch(self, confirmed: ConfirmedSetup, tick_size: float) -> Optional[CascadeWatch]:
        if confirmed.timeframe not in ("5m", "15m"):
            return None
        htf_extreme = confirmed.sl_price if confirmed.sl_price is not None else (
            min(confirmed.c1.low, confirmed.c2.low, confirmed.c3.low)
            if confirmed.direction == SetupDirection.BULL
            else max(confirmed.c1.high, confirmed.c2.high, confirmed.c3.high)
        )
        zone_low = min(confirmed.c1.low, confirmed.c2.low, confirmed.c3.low)
        zone_high = max(confirmed.c1.high, confirmed.c2.high, confirmed.c3.high)
        timeout_min = self._timeout_minutes.get(confirmed.timeframe, 15)
        watch = CascadeWatch(
            watch_id=str(uuid.uuid4()),
            symbol=confirmed.symbol,
            trigger_tf=confirmed.timeframe,
            direction=confirmed.direction,
            poi_id=confirmed.poi_id,
            zone_low=zone_low,
            zone_high=zone_high,
            htf_extreme=htf_extreme,
            parent_event_id=confirmed.event_id,
            deadline_ts=confirmed.confirmed_at + timeout_min * 60.0,
            proximity_ticks=self._proximity_ticks,
            tick_size=tick_size,
        )
        self._watches[watch.watch_id] = watch
        return watch

    def on_1m_candle_closed(self, candle, interactions_by_poi_bull: Dict[str, object],
                             interactions_by_poi_bear: Dict[str, object]) -> List[ConfirmedSetup]:
        results: List[ConfirmedSetup] = []
        now_ts = candle.close_time / 1000.0 if candle.close_time else time.time()

        for watch in list(self._watches.values()):
            if watch.symbol != candle.symbol or watch.status != "WATCHING":
                continue

            if now_ts >= watch.deadline_ts:
                watch.status = "CANCELLED_TIMEOUT"
                continue

            proximity_price = watch.proximity_ticks * watch.tick_size
            if candle.close < (watch.zone_low - proximity_price) or candle.close > (watch.zone_high + proximity_price):
                watch.status = "CANCELLED_PROXIMITY"
                continue

            if watch.direction == SetupDirection.BULL and candle.close < watch.htf_extreme:
                watch.status = "CANCELLED_HTF_BREAK"
                continue
            if watch.direction == SetupDirection.BEAR and candle.close > watch.htf_extreme:
                watch.status = "CANCELLED_HTF_BREAK"
                continue

            if watch.direction == SetupDirection.BULL:
                confirmed_list = self._bull_1m_fsm.on_candle_closed(candle, interactions_by_poi_bull)
            else:
                confirmed_list = self._bear_1m_fsm.on_candle_closed(candle, interactions_by_poi_bear)

            for confirmed in confirmed_list:
                if confirmed.poi_id != watch.poi_id:
                    continue
                watch.status = "SUCCESS"
                confirmed.is_mtf_cascade_result = True
                confirmed.cascade_parent_event_id = watch.parent_event_id
                confirmed.sl_price = (
                    min(confirmed.c1.low, confirmed.c2.low, confirmed.c3.low)
                    if confirmed.direction == SetupDirection.BULL
                    else max(confirmed.c1.high, confirmed.c2.high, confirmed.c3.high)
                )
                confirmed.metadata["mtf_confidence_bonus"] = True
                results.append(confirmed)

        return results

    def get_active_watches(self, symbol: str) -> List[CascadeWatch]:
        return [w for w in self._watches.values() if w.symbol == symbol and w.status == "WATCHING"]

    def get_watch_history(self, symbol: str) -> List[CascadeWatch]:
        return [w for w in self._watches.values() if w.symbol == symbol]
