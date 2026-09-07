"""File 04 - shared internal base for the Candle1/2/3 role-assignment machine.
PATH: engines/workers/setup/_fsm_base.py (REPLACE ENTIRE FILE)

REVISION 2 - corrected against real hand-verified CoinDCX ETHUSDT 1m PDH/PDL
examples (the File 04 check gate). Revision 1 had TWO bugs, both found and
fixed from the user's own manual trace:

BUG 1 (fixed): Revision 1 required Candle1's color to be hard-locked per
direction (RED for Bull, GREEN for Bear). The real trace (Scenario_04) shows
a GREEN candle can become the anchor "Candle1" in what starts as a
Bull-flavoured search. Direction is NOT decided when the anchor forms - it is
only decided once Candle2's color is known (Candle3 must match Candle2's
color, and the "close above high" test only makes sense if Candle2/3 are
Green; "close below low" only if Red). So the anchor/pairing machinery is
color-AGNOSTIC; only the final confirmation test is direction-specific.

BUG 2 (fixed): Revision 1 recycled the FAILING Candle3 as the new Candle1 on
a failed confirmation. The real trace (Scenario_06 -> Scenario_07) proves the
correct recycle target is the OLD CANDLE2, not the failing Candle3 - and the
failing Candle3 itself is then immediately re-tested as the new Candle2
against that recycled anchor (zero delay, same candle). Section 6 step 5's
"recycle the POI-touching candle" means Candle2 - the one guaranteed to have
touched (Candle1 never has to).

Both bugs were re-verified numerically against real ETHUSDT prices
(01:43-01:59, 07-09-2026, PDH=2513.64) - all 7 hand-traced scenarios matched
exactly, including 2 confirmed Bull setups, 1 confirmed Bear setup, and 4
clean abort/recycle paths. Locked at v0.4.0-alpha.

============================================================================
FINAL ALGORITHM (validated against 7 real hand-traced examples)
============================================================================
State per (symbol, timeframe, poi_id): NONE | ANCHOR(c1) | WAITING_C3(c1, c2).
Candles are processed strictly in closing order - consecutive-candle
adjacency (Section 6.6) falls out naturally because every closed candle is
fed through once, in order.

NONE:
    - candle doesn't touch the POI -> stay NONE (Section 6 step 1).
    - candle touches:
        - look at the immediately preceding closed candle P (need NOT have
          touched - Section 6 step 3's "Candle1 doesn't need to touch").
        - if P exists, is not already LOCKED, and color(P) != color(X):
              -> WAITING_C3(c1=P, c2=X)   [Scenario A/B direct hit]
        - else (P missing/locked/same color):
              -> ANCHOR(X)   [X touched, so it independently qualifies -
                 Section 6 step 4: "this same candle... because it already
                 touched the POI"]

ANCHOR(A) - A is guaranteed to have touched the POI at some point:
    - X is the very next candle (Section 6.6 consecutiveness).
    - X is a doji (no color) -> ABORT to NONE (validated: Scenario_01/04 -
      an unusable next candle kills the whole attempt, it does not "wait").
    - color(X) != color(A):
          -> WAITING_C3(c1=A, c2=X)   (A already touched - X need not)
    - color(X) == color(A):
          - X touched -> ANCHOR(X)   (chain extends forward - Scenario_04)
          - X did NOT touch -> ABORT to NONE (validated: Scenario_01)

WAITING_C3(c1, c2):
    - CONFIRMS if this direction's specific rule matches (color(c2)/color(X)
      both correct for that direction AND the extreme test passes) AND none
      of c1/c2/X are already locked by a different setup -> emit
      ConfirmedSetup, lock all 3, reset to NONE.
    - Otherwise (failed test OR one of the 3 already got locked elsewhere):
          new_anchor = c2  (RECYCLE CANDLE2, NOT the failing candle - Bug 2)
          - X is a doji -> ANCHOR(new_anchor), wait for the next real candle.
          - color(X) != color(new_anchor) and new_anchor not locked:
                -> WAITING_C3(c1=new_anchor, c2=X)   (immediate re-pairing,
                   validated: Scenario_06 -> Scenario_07, zero delay)
          - color(X) == color(new_anchor):
                - X touched -> ANCHOR(X)
                - X did not touch -> ABORT to NONE

Both Bull123FSMWorker and Bear123FSMWorker run this EXACT SAME color-agnostic
chain independently (each keeps its own state), sharing only the
CandleLockRegistry. They only differ in `_confirms_extreme`, which is the
ONLY direction-specific rule left (Section 6 step 5 + Section 1's fixed
color pattern). This is intentionally redundant (both track the same pairs)
rather than one shared chain object, because a single physical chain
genuinely does flip between "could become Bull" and "could become Bear"
candidate framing as it recycles (Scenario_06/07) - running two independent,
identical trackers that only diverge at the confirmation step is the
simplest way to keep this file 100% consistent with Bear123FSMWorker while
still being one clean, testable engine.
============================================================================
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple

from engines.workers.setup.candle_color_classifier_worker import CandleColorClassifierWorker
from engines.workers.setup.candle_lock_registry import CandleLockRegistry
from engines.workers.setup.setup_types import ConfirmedSetup, PendingSetup

_ANCHOR = "ANCHOR"
_WAITING_C3 = "WAITING_C3"


class _Base123FSMWorker:
    direction: str = ""

    def __init__(self, lock_registry: CandleLockRegistry) -> None:
        self._lock_registry = lock_registry
        self._classifier = CandleColorClassifierWorker()
        self._pending: Dict[Tuple[str, str, str], PendingSetup] = {}
        self._last_candle: Dict[Tuple[str, str], object] = {}

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Core machine (Section 6)
    # ------------------------------------------------------------------ #

    def _step(self, candle, poi_id: str, touched: bool, prev_candle) -> Optional[ConfirmedSetup]:
        key = (candle.symbol, candle.timeframe, poi_id)
        color = self._classifier.classify(candle)
        pending = self._pending.get(key)

        if pending is None:
            self._step_none(candle, key, touched, color, prev_candle)
            return None
        if pending.stage == _ANCHOR:
            return self._step_anchor(candle, key, pending, touched, color)
        if pending.stage == _WAITING_C3:
            return self._step_waiting_c3(candle, key, pending, touched, color)
        return None  # pragma: no cover

    def _step_none(self, candle, key, touched: bool, color, prev_candle) -> None:
        if not touched or color is None:
            return
        prev_color = self._classifier.classify(prev_candle) if prev_candle is not None else None
        prev_locked = prev_candle is not None and self._lock_registry.is_locked(
            prev_candle.symbol, prev_candle.timeframe, prev_candle.open_time
        )
        if prev_candle is not None and prev_color is not None and not prev_locked and color != prev_color:
            self._pending[key] = self._new_pending(candle, key[2], stage=_WAITING_C3, c1=prev_candle, c2=candle)
        else:
            self._pending[key] = self._new_pending(candle, key[2], stage=_ANCHOR, c1=candle)

    def _step_anchor(self, candle, key, pending: PendingSetup, touched: bool, color) -> None:
        anchor = pending.c1
        if color is None:
            del self._pending[key]
            return None
        anchor_color = self._classifier.classify(anchor)
        if color != anchor_color:
            pending.c2 = candle
            pending.stage = _WAITING_C3
            return None
        if touched:
            pending.c1 = candle  # extend the chain forward
        else:
            del self._pending[key]
        return None

    def _step_waiting_c3(self, candle, key, pending: PendingSetup, touched: bool, color) -> Optional[ConfirmedSetup]:
        c1, c2 = pending.c1, pending.c2
        if color is not None and self._confirms_extreme(candle, c2):
            if not self._lock_registry.any_locked([c1, c2, candle]):
                self._lock_registry.lock_all([c1, c2, candle])
                del self._pending[key]
                return self._build_confirmed(key[2], c1, c2, candle)

        # Failure path (Section 6 step 5): recycle CANDLE2, not this candle.
        new_anchor = c2
        anchor_color = self._classifier.classify(new_anchor)
        anchor_locked = self._lock_registry.is_locked(new_anchor.symbol, new_anchor.timeframe, new_anchor.open_time)
        if color is None:
            self._pending[key] = self._new_pending(candle, key[2], stage=_ANCHOR, c1=new_anchor)
        elif color != anchor_color and not anchor_locked:
            self._pending[key] = self._new_pending(candle, key[2], stage=_WAITING_C3, c1=new_anchor, c2=candle)
        elif touched:
            self._pending[key] = self._new_pending(candle, key[2], stage=_ANCHOR, c1=candle)
        else:
            del self._pending[key]
        return None

    def _confirms_extreme(self, c3, c2) -> bool:
        raise NotImplementedError

    def _build_confirmed(self, poi_id: str, c1, c2, c3) -> ConfirmedSetup:
        return ConfirmedSetup(
            event_id=ConfirmedSetup.new_event_id(),
            symbol=c3.symbol, timeframe=c3.timeframe, poi_id=poi_id,
            direction=self.direction, c1=c1, c2=c2, c3=c3,
            confirmed_at=time.time(),
        )

    def _new_pending(self, candle, poi_id: str, stage: str, c1, c2=None) -> PendingSetup:
        return PendingSetup(
            pending_id=str(uuid.uuid4()), symbol=candle.symbol, timeframe=candle.timeframe,
            poi_id=poi_id, direction=self.direction, stage=stage, c1=c1, c2=c2,
        )
