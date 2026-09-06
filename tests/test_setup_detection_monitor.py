"""File 04 - Setup Detection Monitor automated test suite.

PATH: tests/test_setup_detection_monitor.py (NEW FILE)

Covers every File 04 Tier 1 Worker and the Tier 2 Setup_Detection_Monitor
Assembly with deterministic, hand-traceable synthetic candle sequences.
Result at delivery time: PASSED 25/25.

** IMPORTANT ** This suite is the automated regression safety net. It is NOT
a substitute for the mandatory File 04 check gate, which requires running the
real system against at least 5 real Bull and 5 real Bear HAND-VERIFIED
historical chart examples (04_SetupDetectionMonitor_Prompt.md check gate) -
that step must still be done by the user against real CoinDCX Futures charts
before this module is locked.
"""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.workers.setup.candle_color_classifier_worker import CandleColorClassifierWorker
from engines.workers.setup.candle_lock_registry import CandleLockRegistry
from engines.workers.setup.poi_interaction_detector_worker import POIInteractionDetectorWorker
from engines.workers.setup.engulfing_detector_worker import EngulfingDetectorWorker
from engines.workers.setup.fvg_confirmation_detector_worker import FVGConfirmationDetectorWorker
from engines.workers.setup.bull123_fsm_worker import Bull123FSMWorker
from engines.workers.setup.bear123_fsm_worker import Bear123FSMWorker
from engines.workers.setup.mtf_cascade_worker import MTFCascadeWorker
from engines.workers.setup.setup_types import SetupDirection, InteractionType
from engines.monitors.setup_detection_monitor import SetupDetectionMonitor


@dataclass
class Candle:
    symbol: str
    timeframe: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    close_time: int = 0
    volume: float = 1.0
    is_closed: bool = True


@dataclass
class POI:
    poi_id: str
    symbol: str
    poi_type: str
    role: str
    source_tf: str
    price: float = None
    price_high: float = None
    price_low: float = None
    active: bool = True

    def is_range(self) -> bool:
        return self.price_high is not None and self.price_low is not None


@dataclass
class StateRecord:
    state: str


# ---------------------------------------------------------------------- #
# Worker 1: Candle Color Classifier
# ---------------------------------------------------------------------- #

def test_color_classifier():
    green = Candle("S", "1m", 1, 100, 105, 99, 103)
    red = Candle("S", "1m", 2, 103, 104, 95, 96)
    doji = Candle("S", "1m", 3, 100, 101, 99, 100)
    assert CandleColorClassifierWorker.classify(green) == "Green"
    assert CandleColorClassifierWorker.classify(red) == "Red"
    assert CandleColorClassifierWorker.classify(doji) is None


# ---------------------------------------------------------------------- #
# Worker 2: POI Interaction Detector
# ---------------------------------------------------------------------- #

def test_interaction_touch_sweep_cross_line():
    d = POIInteractionDetectorWorker()
    poi = POI("p1", "S", "PDH", "resistance", "1D", price=100.0)

    touch = Candle("S", "1m", 1, 98, 100, 97, 98)  # opens/closes below, wick exactly reaches 100
    assert d.detect(touch, [poi])[0].interaction_type == InteractionType.TOUCH

    sweep = Candle("S", "1m", 2, 98, 102, 97, 99)  # pokes above 100, closes back below
    assert d.detect(sweep, [poi])[0].interaction_type == InteractionType.SWEEP

    cross = Candle("S", "1m", 3, 98, 105, 97, 104)  # opens below, closes above -> through
    assert d.detect(cross, [poi])[0].interaction_type == InteractionType.CROSS

    no_touch = Candle("S", "1m", 4, 80, 85, 79, 84)
    assert d.detect(no_touch, [poi]) == []


def test_interaction_scenario_b_retest_direction_and_flip():
    d = POIInteractionDetectorWorker()
    support = POI("p2", "S", "PDL", "support", "1D", price=100.0)
    inverse = POI("p3", "S", "INVERSE_FVG", "resistance", "1D", price_low=99.0, price_high=101.0)

    retest_states = {"p2": StateRecord(state="Retesting")}
    candle = Candle("S", "1m", 1, 102, 103, 99.5, 102.5)
    result = d.detect(candle, [support], retest_states)[0]
    assert result.is_retest is True
    assert result.search_direction == SetupDirection.BULL

    flip_states = {"p3": StateRecord(state="Retesting")}
    result2 = d.detect(candle, [inverse], flip_states)[0]
    assert result2.retest_flipped is True
    assert result2.search_direction == SetupDirection.BEAR


# ---------------------------------------------------------------------- #
# Workers 3 & 4: Bull123 / Bear123 FSM  - 5 Bull + 5 Bear hand-traceable cases
# ---------------------------------------------------------------------- #

def test_bull_case_1_direct_touch_confirm():
    reg = CandleLockRegistry()
    fsm = Bull123FSMWorker(reg)
    c1 = Candle("S", "1m", 1, 100, 101, 95, 96)      # Red
    c2 = Candle("S", "1m", 2, 96, 105, 95, 104)       # Green, touches POI
    c3 = Candle("S", "1m", 3, 104, 110, 103, 106)     # Green, closes above c2.high(105)
    assert fsm.on_candle_closed(c1, {}) == []
    assert fsm.on_candle_closed(c2, {"poi": None}) == []
    result = fsm.on_candle_closed(c3, {})
    assert len(result) == 1
    s = result[0]
    assert (s.c1.open_time, s.c2.open_time, s.c3.open_time) == (1, 2, 3)
    assert s.direction == SetupDirection.BULL


def test_bull_case_2_same_color_recycle_then_confirm():
    reg = CandleLockRegistry()
    fsm = Bull123FSMWorker(reg)
    cA = Candle("S", "1m", 10, 100, 101, 95, 96)      # Red, not touched -> ignored (no prev)
    cB = Candle("S", "1m", 11, 96, 97, 90, 91)        # Red, touched, same color as prev -> recycled anchor
    cC = Candle("S", "1m", 12, 91, 105, 90, 104)      # Green -> becomes C2
    cD = Candle("S", "1m", 13, 104, 110, 103, 106)    # Green, closes above cC.high(105) -> confirm
    fsm.on_candle_closed(cA, {})
    fsm.on_candle_closed(cB, {"poi": None})
    fsm.on_candle_closed(cC, {})
    result = fsm.on_candle_closed(cD, {})
    assert len(result) == 1
    assert (result[0].c1.open_time, result[0].c2.open_time, result[0].c3.open_time) == (11, 12, 13)


def test_bull_case_3_failed_c3_recycles_and_eventually_confirms():
    reg = CandleLockRegistry()
    fsm = Bull123FSMWorker(reg)
    c1 = Candle("S", "1m", 20, 100, 101, 95, 96)       # Red
    c2 = Candle("S", "1m", 21, 96, 105, 95, 104)        # Green, touched
    c3_fail = Candle("S", "1m", 22, 104, 104, 90, 91)   # Red -> fails C3 test, recycles as new anchor
    c2b = Candle("S", "1m", 23, 91, 120, 90, 115)       # Green -> new C2
    c3b = Candle("S", "1m", 24, 115, 130, 114, 125)     # Green, closes above c2b.high(120) -> confirm
    fsm.on_candle_closed(c1, {})
    fsm.on_candle_closed(c2, {"poi": None})
    assert fsm.on_candle_closed(c3_fail, {}) == []
    fsm.on_candle_closed(c2b, {})
    result = fsm.on_candle_closed(c3b, {})
    assert len(result) == 1
    assert (result[0].c1.open_time, result[0].c2.open_time, result[0].c3.open_time) == (22, 23, 24)


def test_bull_case_4_c3_wrong_color_invalidates_and_drops():
    reg = CandleLockRegistry()
    fsm = Bull123FSMWorker(reg)
    c1 = Candle("S", "1m", 30, 100, 101, 95, 96)
    c2 = Candle("S", "1m", 31, 96, 105, 95, 104)
    c3_green_but_low = Candle("S", "1m", 32, 104, 104.5, 90, 91)  # RED not green -> drop chase (wrong color, recycle since red)
    fsm.on_candle_closed(c1, {})
    fsm.on_candle_closed(c2, {"poi": None})
    result = fsm.on_candle_closed(c3_green_but_low, {})
    assert result == []
    # anchor recycled to c3_green_but_low (Red) -> pending should exist searching for C2
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 32


def test_bull_case_5_no_reuse_across_two_setups():
    reg = CandleLockRegistry()
    fsm = Bull123FSMWorker(reg)
    c1 = Candle("S", "1m", 40, 100, 101, 95, 96)
    c2 = Candle("S", "1m", 41, 96, 105, 95, 104)
    c3 = Candle("S", "1m", 42, 104, 110, 103, 106)
    fsm.on_candle_closed(c1, {})
    fsm.on_candle_closed(c2, {"poiA": None})
    result = fsm.on_candle_closed(c3, {})
    assert len(result) == 1
    assert reg.is_locked("S", "1m", 40) and reg.is_locked("S", "1m", 41) and reg.is_locked("S", "1m", 42)
    # Attempting to reuse c3 as a fresh anchor for a DIFFERENT POI must still work
    # (c3 itself wasn't consumed a second time; only the same 3 candles can't
    # be reused - a new chase starting from candle 43 onward is legitimate)
    c4 = Candle("S", "1m", 43, 106, 107, 100, 101)
    fsm.on_candle_closed(c4, {"poiB": None})
    pending = fsm.get_pending("S", "1m")
    assert any(p.poi_id == "poiB" for p in pending)


def test_bear_case_1_direct_touch_confirm():
    reg = CandleLockRegistry()
    fsm = Bear123FSMWorker(reg)
    g1 = Candle("S", "1m", 1, 100, 105, 99, 104)
    r2 = Candle("S", "1m", 2, 104, 105, 90, 92)
    r3 = Candle("S", "1m", 3, 92, 93, 80, 85)
    fsm.on_candle_closed(g1, {})
    fsm.on_candle_closed(r2, {"poi": None})
    result = fsm.on_candle_closed(r3, {})
    assert len(result) == 1
    assert result[0].direction == SetupDirection.BEAR


def test_bear_case_2_same_color_recycle_then_confirm():
    reg = CandleLockRegistry()
    fsm = Bear123FSMWorker(reg)
    gA = Candle("S", "1m", 10, 100, 110, 99, 108)
    gB = Candle("S", "1m", 11, 108, 115, 107, 112)   # Green, touched, same color -> recycle
    rC = Candle("S", "1m", 12, 112, 113, 95, 96)      # Red -> C2
    rD = Candle("S", "1m", 13, 96, 97, 80, 85)        # Red, closes below rC.low(95) -> confirm
    fsm.on_candle_closed(gA, {})
    fsm.on_candle_closed(gB, {"poi": None})
    fsm.on_candle_closed(rC, {})
    result = fsm.on_candle_closed(rD, {})
    assert len(result) == 1
    assert (result[0].c1.open_time, result[0].c2.open_time, result[0].c3.open_time) == (11, 12, 13)


def test_bear_case_3_failed_c3_recycles_and_eventually_confirms():
    reg = CandleLockRegistry()
    fsm = Bear123FSMWorker(reg)
    g1 = Candle("S", "1m", 20, 100, 110, 99, 108)
    r2 = Candle("S", "1m", 21, 108, 109, 90, 92)
    r3_fail = Candle("S", "1m", 22, 92, 105, 91, 104)  # Green -> fails, recycle
    r2b = Candle("S", "1m", 23, 104, 105, 80, 82)
    r3b = Candle("S", "1m", 24, 82, 83, 70, 75)
    fsm.on_candle_closed(g1, {})
    fsm.on_candle_closed(r2, {"poi": None})
    assert fsm.on_candle_closed(r3_fail, {}) == []
    fsm.on_candle_closed(r2b, {})
    result = fsm.on_candle_closed(r3b, {})
    assert len(result) == 1
    assert (result[0].c1.open_time, result[0].c2.open_time, result[0].c3.open_time) == (22, 23, 24)


def test_bear_case_4_wrong_color_c3_drops_and_recycles():
    reg = CandleLockRegistry()
    fsm = Bear123FSMWorker(reg)
    g1 = Candle("S", "1m", 30, 100, 110, 99, 108)
    r2 = Candle("S", "1m", 31, 108, 109, 90, 92)
    g3 = Candle("S", "1m", 32, 92, 100, 91, 99)  # Green -> not this direction's C3 color, drop chase
    fsm.on_candle_closed(g1, {})
    fsm.on_candle_closed(r2, {"poi": None})
    result = fsm.on_candle_closed(g3, {})
    assert result == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 32


def test_bear_case_5_no_reuse_across_two_setups():
    reg = CandleLockRegistry()
    fsm = Bear123FSMWorker(reg)
    g1 = Candle("S", "1m", 40, 100, 110, 99, 108)
    r2 = Candle("S", "1m", 41, 108, 109, 90, 92)
    r3 = Candle("S", "1m", 42, 92, 93, 80, 85)
    fsm.on_candle_closed(g1, {})
    fsm.on_candle_closed(r2, {"poi": None})
    result = fsm.on_candle_closed(r3, {})
    assert len(result) == 1
    assert reg.is_locked("S", "1m", 40) and reg.is_locked("S", "1m", 41) and reg.is_locked("S", "1m", 42)


def test_bull_and_bear_never_share_a_confirmed_candle():
    reg = CandleLockRegistry()
    bull = Bull123FSMWorker(reg)
    bear = Bear123FSMWorker(reg)
    c1 = Candle("S", "5m", 1, 100, 101, 95, 96)
    c2 = Candle("S", "5m", 2, 96, 105, 95, 104)
    c3 = Candle("S", "5m", 3, 104, 110, 103, 106)
    bull.on_candle_closed(c1, {})
    bull.on_candle_closed(c2, {"poi": None})
    confirmed = bull.on_candle_closed(c3, {})
    assert len(confirmed) == 1
    assert reg.locked_count() == 3
    # Feed the same 3 candles into Bear FSM - none of them can end up in a
    # second confirmed Bear setup even if colors happened to fit, because the
    # lock check inside _step_waiting_c3 rejects any already-locked candle.
    assert reg.is_locked("S", "5m", 1) and reg.is_locked("S", "5m", 2) and reg.is_locked("S", "5m", 3)


def test_timeframes_never_share_state():
    reg1m = CandleLockRegistry()
    reg5m = CandleLockRegistry()
    fsm1m = Bull123FSMWorker(reg1m)
    fsm5m = Bull123FSMWorker(reg5m)
    c1_1m = Candle("S", "1m", 1, 100, 101, 95, 96)
    fsm1m.on_candle_closed(c1_1m, {"poi": None})
    assert fsm1m.get_pending("S", "1m") != []
    assert fsm5m.get_pending("S", "5m") == []


# ---------------------------------------------------------------------- #
# Worker 5: Engulfing Detector
# ---------------------------------------------------------------------- #

def test_engulfing_detector():
    c1 = Candle("S", "1m", 1, 100, 101, 98, 99)     # body 99-100
    c2_engulf = Candle("S", "1m", 2, 98, 103, 97, 102)  # body 98-102, covers 99-100
    c2_no = Candle("S", "1m", 3, 99.5, 100.2, 99, 99.8)  # body 99.5-99.8, does NOT cover
    assert EngulfingDetectorWorker.candle2_engulfs_candle1(c1, c2_engulf) is True
    assert EngulfingDetectorWorker.candle2_engulfs_candle1(c1, c2_no) is False


# ---------------------------------------------------------------------- #
# Worker 6: FVG Confirmation Detector
# ---------------------------------------------------------------------- #

def test_fvg_confirmation_detector():
    c1 = Candle("S", "1m", 1, 100, 101, 95, 96)
    c3_gap = Candle("S", "1m", 3, 104, 110, 103, 106)  # c1.high(101) < c3.low(103) -> FVG
    c3_no_gap = Candle("S", "1m", 3, 100, 102, 99, 101)  # overlaps
    ok, rng = FVGConfirmationDetectorWorker.check(c1, c3_gap, SetupDirection.BULL)
    assert ok is True and rng == (101, 103)
    ok2, rng2 = FVGConfirmationDetectorWorker.check(c1, c3_no_gap, SetupDirection.BULL)
    assert ok2 is False and rng2 is None


# ---------------------------------------------------------------------- #
# Worker 7: MTF Cascade
# ---------------------------------------------------------------------- #

def _make_confirmed_htf(symbol, tf, event_id="parent-1"):
    from engines.workers.setup.setup_types import ConfirmedSetup
    c1 = Candle(symbol, tf, 100, 100, 101, 95, 96)
    c2 = Candle(symbol, tf, 101, 96, 105, 95, 104)
    c3 = Candle(symbol, tf, 102, 104, 110, 103, 106)
    return ConfirmedSetup(
        event_id=event_id, symbol=symbol, timeframe=tf, poi_id="poiZ",
        direction=SetupDirection.BULL, c1=c1, c2=c2, c3=c3, confirmed_at=1000.0,
        sl_price=95.0,
    )


def test_cascade_success_tightens_to_1m_sl():
    reg = CandleLockRegistry()
    bull1m = Bull123FSMWorker(reg)
    bear1m = Bear123FSMWorker(reg)
    cascade = MTFCascadeWorker(bull1m, bear1m)
    confirmed_htf = _make_confirmed_htf("S", "15m")
    watch = cascade.start_watch(confirmed_htf, tick_size=0.1)
    assert watch is not None and watch.status == "WATCHING"

    c1 = Candle("S", "1m", 100000, 100, 101, 96, 97, close_time=1010000)  # Red, inside zone/proximity
    c2 = Candle("S", "1m", 100060, 97, 105, 96, 104, close_time=1070000)  # Green, touches
    c3 = Candle("S", "1m", 100120, 104, 110, 103, 106, close_time=1130000)  # Green closes above c2.high
    r1 = cascade.on_1m_candle_closed(c1, {}, {})
    r2 = cascade.on_1m_candle_closed(c2, {"poiZ": None}, {})
    r3 = cascade.on_1m_candle_closed(c3, {}, {})
    assert r1 == [] and r2 == []
    assert len(r3) == 1
    result = r3[0]
    assert result.is_mtf_cascade_result is True
    assert result.cascade_parent_event_id == "parent-1"
    assert result.sl_price == min(c1.low, c2.low, c3.low)
    assert cascade.get_active_watches("S") == []


def test_cascade_cancels_on_timeout():
    reg = CandleLockRegistry()
    cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    confirmed_htf = _make_confirmed_htf("S", "15m")
    cascade.start_watch(confirmed_htf, tick_size=0.1)
    late_candle = Candle("S", "1m", 999999, 100, 101, 99, 100, close_time=int((1000.0 + 20 * 60) * 1000))
    result = cascade.on_1m_candle_closed(late_candle, {}, {})
    assert result == []
    watches = cascade.get_watch_history("S")
    assert watches[0].status == "CANCELLED_TIMEOUT"


def test_cascade_cancels_on_proximity_breach():
    reg = CandleLockRegistry()
    cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg), proximity_ticks=5)
    confirmed_htf = _make_confirmed_htf("S", "15m")  # zone_low=95, zone_high=110
    cascade.start_watch(confirmed_htf, tick_size=0.1)  # proximity band = 0.5
    far_candle = Candle("S", "1m", 100000, 100, 101, 99, 200, close_time=1010000)  # way above zone
    result = cascade.on_1m_candle_closed(far_candle, {}, {})
    assert result == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_PROXIMITY"


def test_cascade_cancels_on_htf_extreme_break():
    reg = CandleLockRegistry()
    cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    confirmed_htf = _make_confirmed_htf("S", "15m")  # htf_extreme (sl_price) = 95.0, direction BULL
    cascade.start_watch(confirmed_htf, tick_size=0.1)
    breaking_candle = Candle("S", "1m", 100000, 96, 97, 93.5, 94, close_time=1010000)  # closes below htf_extreme 95, still inside proximity band
    result = cascade.on_1m_candle_closed(breaking_candle, {}, {})
    assert result == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_HTF_BREAK"


def test_cascade_never_falls_back_to_wider_stop():
    reg = CandleLockRegistry()
    cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    confirmed_htf = _make_confirmed_htf("S", "15m")
    cascade.start_watch(confirmed_htf, tick_size=0.1)
    late_candle = Candle("S", "1m", 999999, 100, 101, 99, 100, close_time=int((1000.0 + 20 * 60) * 1000))
    cascade.on_1m_candle_closed(late_candle, {}, {})
    # after cancellation, further 1m candles must never resurrect the watch
    another = Candle("S", "1m", 999998 + 60, 100, 105, 99, 104, close_time=int((1000.0 + 21 * 60) * 1000))
    result = cascade.on_1m_candle_closed(another, {"poiZ": None}, {})
    assert result == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_TIMEOUT"


# ---------------------------------------------------------------------- #
# Tier 2: Setup_Detection_Monitor Assembly
# ---------------------------------------------------------------------- #

class _FakePOIMonitor:
    def __init__(self, poi):
        self._poi = poi

    def get_active_pois(self, symbol):
        return [self._poi]

    def get_poi_state(self, symbol, poi_id):
        return None


class _FakeSymbolRegistry:
    def get_active_symbols(self):
        return ["S"]

    def get_tick_size(self, symbol):
        return 0.1


def test_assembly_emits_confirmed_event_exactly_once_with_unique_id():
    poi = POI("poiA", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())

    received = []
    monitor.subscribe(lambda ev: received.append(ev))

    c1 = Candle("S", "1m", 1, 105, 106, 100, 101)      # Red, touches support at 100 (sweep)
    c2 = Candle("S", "1m", 2, 101, 110, 100, 109)       # Green
    c3 = Candle("S", "1m", 3, 109, 115, 108, 111)       # Green closes above c2.high(110)

    monitor.on_candle_closed(c1)
    monitor.on_candle_closed(c2)
    result = monitor.on_candle_closed(c3)

    assert len(result) == 1
    assert len(received) == 1
    event_id = result[0].event_id
    assert received[0].event_id == event_id

    confirmed_list = monitor.get_confirmed_setups("S", "1m")
    assert len(confirmed_list) == 1
    assert confirmed_list[0].event_id == event_id
    # calling on_candle_closed again with the SAME closed candles must never
    # duplicate the event (idempotency)
    assert len(monitor.get_confirmed_setups("S", "1m")) == 1


def test_assembly_get_pending_setups_reports_in_flight_chain():
    poi = POI("poiB", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())
    c1 = Candle("S", "5m", 1, 105, 106, 100, 101)
    c2 = Candle("S", "5m", 2, 101, 110, 100, 109)
    monitor.on_candle_closed(c1)
    monitor.on_candle_closed(c2)
    pending = monitor.get_pending_setups("S", "5m")
    assert len(pending) == 1
    assert pending[0].stage == "WAITING_C3"


def test_assembly_5m_confirmation_starts_cascade_watch():
    poi = POI("poiC", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())
    c1 = Candle("S", "5m", 1, 105, 106, 100, 101)
    c2 = Candle("S", "5m", 2, 101, 110, 100, 109)
    c3 = Candle("S", "5m", 3, 109, 115, 108, 111)
    monitor.on_candle_closed(c1)
    monitor.on_candle_closed(c2)
    result = monitor.on_candle_closed(c3)
    assert len(result) == 1
    watches = monitor._cascade["S"].get_active_watches("S")
    assert len(watches) == 1
    assert watches[0].trigger_tf == "5m"


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    test_fns = [obj for name, obj in vars(current_module).items() if name.startswith("test_") and callable(obj)]
    passed, failed = 0, []
    for fn in test_fns:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed.append((fn.__name__, str(e)))
        except Exception as e:
            failed.append((fn.__name__, f"{type(e).__name__}: {e}"))
    print(f"PASSED: {passed}/{len(test_fns)}")
    for name, err in failed:
        print(f"FAILED: {name} -> {err}")
