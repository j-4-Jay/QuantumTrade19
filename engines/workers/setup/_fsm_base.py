"""File 04 - shared internal base for the Candle1/2/3 role-assignment machine.

PATH: engines/workers/setup/_fsm_base.py (NEW FILE, internal support only)

Not one of the 7 numbered Tier 1 Workers. Exists so Bull123_FSM_Worker and
Bear123_FSM_Worker share one single, tested implementation of the machine in
123Bull_Setup_Master_Prompt.md / 123Bear_Setup_Master_Prompt.md Section 6 -
both master prompts state they are "the exact mirror... every rule flips
color, direction, and role." One tested engine, split by direction, is what
actually guarantees zero deviation between the two mirrored workers.

============================================================================
IMPLEMENTATION NOTE - read before ever touching this file again
============================================================================
Section 6 is written as sequential prose, not literal pseudocode. Points that
needed one single, consistent resolution to become runnable code:

1. "The candle right before it" (step 3) = the immediately preceding CLOSED
   candle on the same (symbol, timeframe) series - tracked as `_last_candle`,
   independent of any POI. Candle1 is that preceding candle even though it
   never had to touch the POI itself (step 3's own words).

2. Once a chase is running (an anchor Candle1 held via step 4's recycle),
   every subsequent candle is tested purely by color against that anchor - a
   fresh POI touch is NOT required again (same step-3 rule). The anchor
   recycles forward (steps 4/5) until Candle2 is found or the chase drops
   because neither required color appears.

3. Section 1 fixes the exact color pattern per direction (Bull = Red,Green,
   Green; Bear = Green,Red,Red). Section 6's generic "colors different"
   wording is applied WITH that direction's color constraint - a
   Green-then-Red transition is not evaluated by the Bull machine at all;
   Bear123FSMWorker independently watches the same candles for it (Section
   6.7: "123Bear and 123Bull setups also never share candles").

** This resolution has NOT been checked against real hand-verified historical
chart examples. Per the File 04 check gate, run get_pending_setups()/
get_confirmed_setups() against at least 5 real Bull and 5 real Bear historical
examples and confirm every confirmation/invalidation/recycle event matches
manual chart analysis EXACTLY before this file is locked. Do not lock on the
synthetic unit tests alone. **
============================================================================
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple

from engines.workers.setup.candle_color_classifier_worker import CandleColorClassifierWorker
from engines.workers.setup.candle_lock_registry import CandleLockRegistry
from engines.workers.setup.setup_types import ConfirmedSetup, PendingSetup

_SEARCHING_C2 = "SEARCHING_C2"
_WAITING_C3 = "WAITING_C3"


class _Base123FSMWorker:
    direction: str = ""
    c1_color: str = ""
    c2_color: str = ""

    def __init__(self, lock_registry: CandleLockRegistry) -> None:
        self._lock_registry = lock_registry
        self._classifier = CandleColorClassifierWorker()
        self._pending: Dict[Tuple[str, str, str], PendingSetup] = {}
        self._last_candle: Dict[Tuple[str, str], object] = {}

    def on_candle_closed(self, candle, interactions_by_poi: Dict[str, object]) -> List[ConfirmedSetup]:
        tf_key = (candle.symbol, candle.timeframe)
        prev_candle = self._last_candle.get(tf_key)

        confirmed: List[ConfirmedSetup] = []
        touched_poi_ids = set(interactions_by_poi.keys())
        active_poi_ids = {k[2] for k in self._pending if k[0] == candle.symbol and k[1] == candle.timeframe}
        for poi_id in touched_poi_ids | active_poi_ids:
            result = self._step(candle, poi_id, touched=poi_id in touched_poi_ids, prev_candle=prev_candle)
            if result is not None:
                confirmed.append(result)

        self._last_candle[tf_key] = candle
        return confirmed

    def get_pending(self, symbol: str, timeframe: str) -> List[PendingSetup]:
        return [p for k, p in self._pending.items() if k[0] == symbol and k[1] == timeframe]

    def _step(self, candle, poi_id: str, touched: bool, prev_candle) -> Optional[ConfirmedSetup]:
        key = (candle.symbol, candle.timeframe, poi_id)
        color = self._classifier.classify(candle)
        pending = self._pending.get(key)

        if pending is None:
            return self._step_no_chase(candle, key, touched, color, prev_candle)
        if pending.stage == _SEARCHING_C2:
            return self._step_searching_c2(candle, key, pending, color)
        if pending.stage == _WAITING_C3:
            return self._step_waiting_c3(candle, key, pending, color)
        return None  # pragma: no cover

    def _step_no_chase(self, candle, key, touched: bool, color, prev_candle) -> Optional[ConfirmedSetup]:
        if not touched:
            return None
        prev_color = self._classifier.classify(prev_candle) if prev_candle is not None else None
        if (
            prev_candle is not None
            and color is not None
            and prev_color is not None
            and color != prev_color
            and prev_color == self.c1_color
            and color == self.c2_color
        ):
            # Section 6 step 3: colors differ in THIS direction's required
            # order -> preceding candle = C1, this candle = C2.
            self._pending[key] = self._new_pending(candle, key[2], stage=_WAITING_C3, c1=prev_candle, c2=candle)
            return None
        # Either colors matched (step 4 recycle case) or they differed but in
        # the OTHER direction's order (not this FSM's concern at all - the
        # opposite-direction FSM instance owns that transition). Either way,
        # THIS touching candle can still start a fresh Bull/Bear anchor of
        # its own if its own color matches this direction's required Candle1
        # color (Section 6 step 4: "this same candle... becomes Candle1").
        if color == self.c1_color:
            self._pending[key] = self._new_pending(candle, key[2], stage=_SEARCHING_C2, c1=candle)
        return None

    def _step_searching_c2(self, candle, key, pending: PendingSetup, color) -> Optional[ConfirmedSetup]:
        if color is None:
            return None
        if color == self.c2_color and color != self.c1_color:
            pending.c2 = candle
            pending.stage = _WAITING_C3
            return None
        if color == self.c1_color:
            pending.c1 = candle
        else:
            del self._pending[key]
        return None

    def _step_waiting_c3(self, candle, key, pending: PendingSetup, color) -> Optional[ConfirmedSetup]:
        c1, c2 = pending.c1, pending.c2
        confirmed = color == self.c2_color and self._confirms_extreme(candle, c2)
        if confirmed:
            if self._lock_registry.any_locked([c1, c2, candle]):
                confirmed = False
            else:
                self._lock_registry.lock_all([c1, c2, candle])
                del self._pending[key]
                return self._build_confirmed(key[2], c1, c2, candle)

        if color == self.c1_color:
            self._pending[key] = self._new_pending(candle, key[2], stage=_SEARCHING_C2, c1=candle)
        else:
            del self._pending[key]
        return None

    def _confirms_extreme(self, c3, c2) -> bool:
        raise NotImplementedError

    def _build_confirmed(self, poi_id: str, c1, c2, c3) -> ConfirmedSetup:
        return ConfirmedSetup(
            event_id=ConfirmedSetup.new_event_id(),
            symbol=c3.symbol,
            timeframe=c3.timeframe,
            poi_id=poi_id,
            direction=self.direction,
            c1=c1, c2=c2, c3=c3,
            confirmed_at=time.time(),
        )

    def _new_pending(self, candle, poi_id: str, stage: str, c1, c2=None) -> PendingSetup:
        return PendingSetup(
            pending_id=str(uuid.uuid4()),
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            poi_id=poi_id,
            direction=self.direction,
            stage=stage,
            c1=c1,
            c2=c2,
        )
