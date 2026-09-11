"""File 04 - Setup Detection Monitor - Worker 2/7: POI Interaction Detector.

PATH: engines/workers/setup/poi_interaction_detector_worker.py (REPLACE ENTIRE FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md / 123Bear_Setup_Master_Prompt.md
Section 4 (Touch/Sweep/Cross) and Section 5 (Scenario A / Scenario B retest,
including the double-cross flip).

IMPLEMENTATION NOTE: Section 4 describes Touch/Sweep/Cross in words, not as a
formula. This worker turns that wording into a deterministic, self-contained
per-candle rule using each closed candle's own OPEN as "the side it came from"
and CLOSE as "the side it left on":

    reached      = candle's [low, high] range touches the POI level/zone
    open_side     = which side of the level the candle OPENED on
    close_side    = which side of the level the candle CLOSED on
    overshoot     = how far past the level the wick travelled beyond a bare touch
                    (measured on the wick facing the level: high-side if the
                    candle approaches from below, low-side if from above)

    - not reached                          -> no interaction
    - open_side == close_side (same side)
        - overshoot <= 0 (wick reaches exactly the level, no further) -> TOUCH
        - overshoot >  0 (wick genuinely pokes through then returns)  -> SWEEP
    - open_side != close_side (closed on the far/opposite side)       -> CROSS

For a price-RANGE POI (FVG / Inverse FVG / Order Block), the "level" used is
the zone edge nearer to the candle's open price, and "reached" means the
candle's [low, high] overlaps [price_low, price_high] at all.

============================================================================
FILE 04 CORE CORRECTION v1 (this revision) - ROLE-AGNOSTIC DIRECTION
============================================================================
REVISION 2 removes the role->direction gating that REVISION 1 incorrectly
applied here. REVISION 1 read poi.role ("support"/"resistance") and emitted
ONE Interaction with a single search_direction, meaning a "resistance" POI
could only ever feed Bear123FSMWorker and a "support" POI could only ever
feed Bull123FSMWorker. That was an implementation assumption made while
wiring File 04, NOT a requirement of the 123Bull/123Bear master prompts, and
it is REJECTED per File_04_CoreCorrection_Spec_Lock_v1.md Section 2.

Corrected rule: every closed candle's interaction with EVERY active POI -
regardless of that POI's role (support/resistance) or type (PDH/PDL/4H
High/4H Low/FVG/etc.) - now feeds BOTH the Bull123FSMWorker AND the
Bear123FSMWorker for that (symbol, timeframe, poi_id). Implemented here by
emitting TWO Interaction records per touched POI (one BULL, one BEAR) with
identical is_retest/retest_flipped/interaction_type - this requires ZERO
changes to SetupDetectionMonitor.on_candle_closed()'s existing split:
    bull_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BULL}
    bear_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BEAR}
because both dict comprehensions now naturally pick up their own entry for
the SAME poi_id whenever a touch occurs.

Scenario A vs Scenario B (including the double-cross flip) is UNCHANGED -
it is still read directly off the already-locked File 03 output and does
NOT depend on direction:
    - POIStateRecord.state == "Retesting" -> Scenario-B retest.
    - poi.poi_type == "INVERSE_FVG"       -> already the flipped zone
      (InverseFVGDetectorWorker, File 03, performed the flip).
poi.role is NO LONGER read here at all - it has zero influence on
123Bull/123Bear detection eligibility, exactly as locked.
"""
from __future__ import annotations

from typing import List, Optional

from engines.workers.setup.setup_types import Interaction, InteractionType, SetupDirection


class POIInteractionDetectorWorker:
    def detect(self, candle, pois: List[object], states: Optional[dict] = None) -> List[Interaction]:
        states = states or {}
        found: List[Interaction] = []
        for poi in pois:
            if not poi.active:
                continue
            itype = self._classify_interaction(candle, poi)
            if itype is None:
                continue
            state_record = states.get(poi.poi_id)
            is_retest = bool(state_record and state_record.state == "Retesting")
            retest_flipped = is_retest and str(poi.poi_type) == "INVERSE_FVG"

            # Role-agnostic (File 04 Core Correction v1): this SAME touch
            # feeds BOTH directions for the SAME poi_id, regardless of
            # poi.role or poi.poi_type. Role-based direction gating is
            # REMOVED entirely from the 123Bull/123Bear pipeline.
            for direction in (SetupDirection.BULL, SetupDirection.BEAR):
                found.append(
                    Interaction(
                        poi_id=poi.poi_id,
                        interaction_type=itype,
                        is_retest=is_retest,
                        retest_flipped=retest_flipped,
                        search_direction=direction,
                    )
                )
        return found

    def _classify_interaction(self, candle, poi) -> Optional[str]:
        if poi.is_range():
            return self._classify_zone(candle, poi.price_low, poi.price_high)
        return self._classify_line(candle, poi.price)

    @staticmethod
    def _classify_line(candle, level: float) -> Optional[str]:
        if level is None:
            return None
        reached = candle.low <= level <= candle.high
        if not reached:
            return None
        open_side = "above" if candle.open > level else ("below" if candle.open < level else "on")
        close_side = "above" if candle.close > level else ("below" if candle.close < level else "on")
        if open_side == "on" or close_side == "on":
            return InteractionType.TOUCH
        if open_side == close_side:
            overshoot = (candle.high - level) if open_side == "below" else (level - candle.low)
            return InteractionType.TOUCH if overshoot <= 0 else InteractionType.SWEEP
        return InteractionType.CROSS

    @staticmethod
    def _classify_zone(candle, price_low: float, price_high: float) -> Optional[str]:
        reached = candle.low <= price_high and candle.high >= price_low
        if not reached:
            return None
        level = price_low if abs(candle.open - price_low) <= abs(candle.open - price_high) else price_high
        return POIInteractionDetectorWorker._classify_line(candle, level)
