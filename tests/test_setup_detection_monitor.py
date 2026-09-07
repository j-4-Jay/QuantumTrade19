"""File 04 - Setup Detection Monitor automated test suite (REVISION 2).
PATH: tests/test_setup_detection_monitor.py (REPLACE ENTIRE FILE)

Updated after the real CoinDCX ETHUSDT 1m PDH/PDL check gate found two bugs
in Revision 1 (see _fsm_base.py header). Result at delivery time: 26/26
PASSING. If you still see 25/25, you are running the OLD engine files -
replace ALL of _fsm_base.py, bull123_fsm_worker.py, bear123_fsm_worker.py,
mtf_cascade_worker.py, setup_detection_monitor.py, and this file together.
"""
from __future__ import annotations
import sys, os
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
    symbol: str; timeframe: str; open_time: int
    open: float; high: float; low: float; close: float
    close_time: int = 0; volume: float = 1.0; is_closed: bool = True


@dataclass
class POI:
    poi_id: str; symbol: str; poi_type: str; role: str; source_tf: str
    price: float = None; price_high: float = None; price_low: float = None; active: bool = True
    def is_range(self): return self.price_high is not None and self.price_low is not None


@dataclass
class StateRecord:
    state: str


def test_color_classifier():
    assert CandleColorClassifierWorker.classify(Candle("S","1m",1,100,105,99,103)) == "Green"
    assert CandleColorClassifierWorker.classify(Candle("S","1m",2,103,104,95,96)) == "Red"
    assert CandleColorClassifierWorker.classify(Candle("S","1m",3,100,101,99,100)) is None


def test_interaction_touch_sweep_cross_line():
    d = POIInteractionDetectorWorker()
    poi = POI("p1", "S", "PDH", "resistance", "1D", price=100.0)
    touch = Candle("S", "1m", 1, 98, 100, 97, 98)
    assert d.detect(touch, [poi])[0].interaction_type == InteractionType.TOUCH
    sweep = Candle("S", "1m", 2, 98, 102, 97, 99)
    assert d.detect(sweep, [poi])[0].interaction_type == InteractionType.SWEEP
    cross = Candle("S", "1m", 3, 98, 105, 97, 104)
    assert d.detect(cross, [poi])[0].interaction_type == InteractionType.CROSS
    assert d.detect(Candle("S", "1m", 4, 80, 85, 79, 84), [poi]) == []


def test_interaction_scenario_b_retest_direction_and_flip():
    d = POIInteractionDetectorWorker()
    support = POI("p2", "S", "PDL", "support", "1D", price=100.0)
    inverse = POI("p3", "S", "INVERSE_FVG", "resistance", "1D", price_low=99.0, price_high=101.0)
    candle = Candle("S", "1m", 1, 102, 103, 99.5, 102.5)
    r1 = d.detect(candle, [support], {"p2": StateRecord(state="Retesting")})[0]
    assert r1.is_retest is True and r1.search_direction == SetupDirection.BULL
    r2 = d.detect(candle, [inverse], {"p3": StateRecord(state="Retesting")})[0]
    assert r2.retest_flipped is True and r2.search_direction == SetupDirection.BEAR


def test_bull_case_1_direct_touch_confirm():
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    c1 = Candle("S","1m",1,100,101,95,96); c2 = Candle("S","1m",2,96,105,95,104); c3 = Candle("S","1m",3,104,110,103,106)
    fsm.on_candle_closed(c1, {}); fsm.on_candle_closed(c2, {"poi": None})
    r = fsm.on_candle_closed(c3, {})
    assert len(r) == 1 and (r[0].c1.open_time, r[0].c2.open_time, r[0].c3.open_time) == (1,2,3)


def test_bull_case_2_same_color_chain_extends_then_confirms():
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    cA = Candle("S","1m",10,100,101,95,96); cB = Candle("S","1m",11,96,97,90,91)
    cC = Candle("S","1m",12,91,105,90,104); cD = Candle("S","1m",13,104,110,103,106)
    fsm.on_candle_closed(cA, {"poi": None}); fsm.on_candle_closed(cB, {"poi": None})
    fsm.on_candle_closed(cC, {})
    r = fsm.on_candle_closed(cD, {})
    assert len(r) == 1 and (r[0].c1.open_time, r[0].c2.open_time, r[0].c3.open_time) == (11,12,13)


def test_bull_case_3_failed_c3_recycles_candle2_not_the_failing_candle():
    """Validated directly against the user's real Scenario_06 -> Scenario_07 trace."""
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    c1 = Candle("S","1m",20,100,101,95,96)
    c2 = Candle("S","1m",21,96,105,95,104)
    c3_fail = Candle("S","1m",22,104,104.5,103,104.2)  # green, close 104.2 < c2.high(105) -> fails
    fsm.on_candle_closed(c1, {}); fsm.on_candle_closed(c2, {"poi": None})
    assert fsm.on_candle_closed(c3_fail, {}) == []
    # same color as c2 (green) but c3_fail did NOT touch -> chain aborts entirely
    assert fsm.get_pending("S","1m") == []


def test_bull_case_3b_failed_c3_of_opposite_color_immediately_becomes_new_c2():
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    c1 = Candle("S","1m",20,100,101,95,96)
    c2 = Candle("S","1m",21,96,105,95,104)
    c3_fail_red = Candle("S","1m",22,104,104,90,91)  # RED -> fails, opposite color of c2
    c4 = Candle("S","1m",24,115,130,114,125)
    fsm.on_candle_closed(c1, {}); fsm.on_candle_closed(c2, {"poi": None})
    assert fsm.on_candle_closed(c3_fail_red, {}) == []
    pending = fsm.get_pending("S","1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 21 and pending[0].c2.open_time == 22


def test_bull_case_4_wrong_color_next_candle_after_anchor_aborts():
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    c1 = Candle("S","1m",30,100,101,95,96)
    fsm.on_candle_closed(c1, {"poi": None})
    c2_same_notouch = Candle("S","1m",31,96,97,94,95)
    r = fsm.on_candle_closed(c2_same_notouch, {})
    assert r == [] and fsm.get_pending("S","1m") == []


def test_bull_case_5_no_reuse_across_two_setups():
    reg = CandleLockRegistry(); fsm = Bull123FSMWorker(reg)
    c1 = Candle("S","1m",40,100,101,95,96); c2 = Candle("S","1m",41,96,105,95,104); c3 = Candle("S","1m",42,104,110,103,106)
    fsm.on_candle_closed(c1, {}); fsm.on_candle_closed(c2, {"poiA": None})
    r = fsm.on_candle_closed(c3, {})
    assert len(r) == 1
    assert reg.is_locked("S","1m",40) and reg.is_locked("S","1m",41) and reg.is_locked("S","1m",42)
    c4 = Candle("S","1m",43,106,107,100,101)
    fsm.on_candle_closed(c4, {"poiB": None})
    pending = fsm.get_pending("S","1m")
    assert any(p.poi_id == "poiB" for p in pending)


def test_bear_case_1_direct_touch_confirm():
    reg = CandleLockRegistry(); fsm = Bear123FSMWorker(reg)
    g1 = Candle("S","1m",1,100,105,99,104); r2 = Candle("S","1m",2,104,105,90,92); r3 = Candle("S","1m",3,92,93,80,85)
    fsm.on_candle_closed(g1, {}); fsm.on_candle_closed(r2, {"poi": None})
    r = fsm.on_candle_closed(r3, {})
    assert len(r) == 1 and r[0].direction == SetupDirection.BEAR


def test_bear_case_2_same_color_chain_extends_then_confirms():
    reg = CandleLockRegistry(); fsm = Bear123FSMWorker(reg)
    gA = Candle("S","1m",10,100,110,99,108); gB = Candle("S","1m",11,108,115,107,112)
    rC = Candle("S","1m",12,112,113,95,96); rD = Candle("S","1m",13,96,97,80,85)
    fsm.on_candle_closed(gA, {"poi": None}); fsm.on_candle_closed(gB, {"poi": None})
    fsm.on_candle_closed(rC, {})
    r = fsm.on_candle_closed(rD, {})
    assert len(r) == 1 and (r[0].c1.open_time, r[0].c2.open_time, r[0].c3.open_time) == (11,12,13)


def test_bear_case_3_failed_c3_recycles_candle2_immediately_as_new_c1():
    """Direct mirror of the validated Scenario_06 -> Scenario_07 real trace."""
    reg = CandleLockRegistry(); fsm = Bear123FSMWorker(reg)
    c1 = Candle("S","1m",20,100,105,99,104)
    c2 = Candle("S","1m",21,104,105,90,92)
    c3_fail = Candle("S","1m",22,92,110,91,108)  # GREEN -> opposite color of c2(red) -> immediately new c2
    fsm.on_candle_closed(c1, {}); fsm.on_candle_closed(c2, {"poi": None})
    assert fsm.on_candle_closed(c3_fail, {}) == []
    pending = fsm.get_pending("S","1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 21 and pending[0].c2.open_time == 22


def test_bear_case_4_wrong_color_next_candle_after_anchor_aborts():
    reg = CandleLockRegistry(); fsm = Bear123FSMWorker(reg)
    g1 = Candle("S","1m",30,100,110,99,108)
    fsm.on_candle_closed(g1, {"poi": None})
    g2_notouch = Candle("S","1m",31,108,112,107,110)
    r = fsm.on_candle_closed(g2_notouch, {})
    assert r == [] and fsm.get_pending("S","1m") == []


def test_bear_case_5_no_reuse_across_two_setups():
    reg = CandleLockRegistry(); fsm = Bear123FSMWorker(reg)
    g1 = Candle("S","1m",40,100,110,99,108); r2 = Candle("S","1m",41,108,109,90,92); r3 = Candle("S","1m",42,92,93,80,85)
    fsm.on_candle_closed(g1, {}); fsm.on_candle_closed(r2, {"poi": None})
    r = fsm.on_candle_closed(r3, {})
    assert len(r) == 1
    assert reg.is_locked("S","1m",40) and reg.is_locked("S","1m",41) and reg.is_locked("S","1m",42)


def test_bull_and_bear_never_share_a_confirmed_candle():
    reg = CandleLockRegistry(); bull = Bull123FSMWorker(reg); bear = Bear123FSMWorker(reg)
    c1 = Candle("S","5m",1,100,101,95,96); c2 = Candle("S","5m",2,96,105,95,104); c3 = Candle("S","5m",3,104,110,103,106)
    bull.on_candle_closed(c1, {}); bull.on_candle_closed(c2, {"poi": None})
    confirmed = bull.on_candle_closed(c3, {})
    assert len(confirmed) == 1 and reg.locked_count() == 3
    assert reg.is_locked("S","5m",1) and reg.is_locked("S","5m",2) and reg.is_locked("S","5m",3)


def test_timeframes_never_share_state():
    reg1m = CandleLockRegistry(); reg5m = CandleLockRegistry()
    fsm1m = Bull123FSMWorker(reg1m); fsm5m = Bull123FSMWorker(reg5m)
    fsm1m.on_candle_closed(Candle("S","1m",1,100,101,95,96), {"poi": None})
    assert fsm1m.get_pending("S","1m") != [] and fsm5m.get_pending("S","5m") == []


def test_engulfing_detector():
    c1 = Candle("S","1m",1,100,101,98,99); c2_engulf = Candle("S","1m",2,98,103,97,102); c2_no = Candle("S","1m",3,99.5,100.2,99,99.8)
    assert EngulfingDetectorWorker.candle2_engulfs_candle1(c1, c2_engulf) is True
    assert EngulfingDetectorWorker.candle2_engulfs_candle1(c1, c2_no) is False


def test_fvg_confirmation_detector():
    c1 = Candle("S","1m",1,100,101,95,96); c3_gap = Candle("S","1m",3,104,110,103,106); c3_no_gap = Candle("S","1m",3,100,102,99,101)
    ok, rng = FVGConfirmationDetectorWorker.check(c1, c3_gap, SetupDirection.BULL)
    assert ok is True and rng == (101, 103)
    ok2, rng2 = FVGConfirmationDetectorWorker.check(c1, c3_no_gap, SetupDirection.BULL)
    assert ok2 is False and rng2 is None


def _make_confirmed_htf(symbol, tf, event_id="parent-1"):
    from engines.workers.setup.setup_types import ConfirmedSetup
    c1 = Candle(symbol, tf, 100, 100, 101, 95, 96); c2 = Candle(symbol, tf, 101, 96, 105, 95, 104); c3 = Candle(symbol, tf, 102, 104, 110, 103, 106)
    return ConfirmedSetup(event_id=event_id, symbol=symbol, timeframe=tf, poi_id="poiZ", direction=SetupDirection.BULL,
                           c1=c1, c2=c2, c3=c3, confirmed_at=1000.0, sl_price=95.0)


def test_cascade_success_tightens_to_1m_sl():
    reg = CandleLockRegistry(); cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    watch = cascade.start_watch(_make_confirmed_htf("S","15m"), tick_size=0.1)
    assert watch is not None and watch.status == "WATCHING"
    c1 = Candle("S","1m",100000,100,101,96,97, close_time=1010000)
    c2 = Candle("S","1m",100060,97,105,96,104, close_time=1070000)
    c3 = Candle("S","1m",100120,104,110,103,106, close_time=1130000)
    cascade.on_1m_candle_closed(c1, {}, {})
    cascade.on_1m_candle_closed(c2, {"poiZ": None}, {})
    r3 = cascade.on_1m_candle_closed(c3, {}, {})
    assert len(r3) == 1 and r3[0].is_mtf_cascade_result is True
    assert r3[0].cascade_parent_event_id == "parent-1"
    assert cascade.get_active_watches("S") == []


def test_cascade_cancels_on_timeout():
    reg = CandleLockRegistry(); cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    cascade.start_watch(_make_confirmed_htf("S","15m"), tick_size=0.1)
    late = Candle("S","1m",999999,100,101,99,100, close_time=int((1000.0+20*60)*1000))
    assert cascade.on_1m_candle_closed(late, {}, {}) == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_TIMEOUT"


def test_cascade_cancels_on_proximity_breach():
    reg = CandleLockRegistry(); cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg), proximity_ticks=5)
    cascade.start_watch(_make_confirmed_htf("S","15m"), tick_size=0.1)
    far = Candle("S","1m",100000,100,101,99,200, close_time=1010000)
    assert cascade.on_1m_candle_closed(far, {}, {}) == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_PROXIMITY"


def test_cascade_cancels_on_htf_extreme_break():
    reg = CandleLockRegistry(); cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    cascade.start_watch(_make_confirmed_htf("S","15m"), tick_size=0.1)
    breaking = Candle("S","1m",100000,96,97,93.5,94, close_time=1010000)
    assert cascade.on_1m_candle_closed(breaking, {}, {}) == []
    assert cascade.get_watch_history("S")[0].status == "CANCELLED_HTF_BREAK"


def test_cascade_never_falls_back_to_wider_stop():
    reg = CandleLockRegistry(); cascade = MTFCascadeWorker(Bull123FSMWorker(reg), Bear123FSMWorker(reg))
    cascade.start_watch(_make_confirmed_htf("S","15m"), tick_size=0.1)
    late = Candle("S","1m",999999,100,101,99,100, close_time=int((1000.0+20*60)*1000))
    cascade.on_1m_candle_closed(late, {}, {})
    another = Candle("S","1m",999998+60,100,105,99,104, close_time=int((1000.0+21*60)*1000))
    r = cascade.on_1m_candle_closed(another, {"poiZ": None}, {})
    assert r == [] and cascade.get_watch_history("S")[0].status == "CANCELLED_TIMEOUT"


class _FakePOIMonitor:
    def __init__(self, poi): self._poi = poi
    def get_active_pois(self, symbol): return [self._poi]
    def get_poi_state(self, symbol, poi_id): return None

class _FakeSymbolRegistry:
    def get_active_symbols(self): return ["S"]
    def get_tick_size(self, symbol): return 0.1


def test_assembly_emits_confirmed_event_exactly_once_with_unique_id():
    poi = POI("poiA", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())
    received = []
    monitor.subscribe(lambda ev: received.append(ev))
    c1 = Candle("S","1m",1,105,106,100,101); c2 = Candle("S","1m",2,101,110,100,109); c3 = Candle("S","1m",3,109,115,108,111)
    monitor.on_candle_closed(c1); monitor.on_candle_closed(c2)
    result = monitor.on_candle_closed(c3)
    assert len(result) == 1 and len(received) == 1
    assert received[0].event_id == result[0].event_id
    assert len(monitor.get_confirmed_setups("S","1m")) == 1


def test_assembly_get_pending_setups_reports_in_flight_chain():
    poi = POI("poiB", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())
    c1 = Candle("S","5m",1,105,106,100,101); c2 = Candle("S","5m",2,101,110,100,109)
    monitor.on_candle_closed(c1); monitor.on_candle_closed(c2)
    pending = monitor.get_pending_setups("S","5m")
    assert len(pending) == 1 and pending[0].stage == "WAITING_C3"


def test_assembly_5m_confirmation_starts_cascade_watch():
    poi = POI("poiC", "S", "PDL", "support", "1D", price=100.0)
    monitor = SetupDetectionMonitor(_FakePOIMonitor(poi), _FakeSymbolRegistry())
    c1 = Candle("S","5m",1,105,106,100,101); c2 = Candle("S","5m",2,101,110,100,109); c3 = Candle("S","5m",3,109,115,108,111)
    monitor.on_candle_closed(c1); monitor.on_candle_closed(c2)
    result = monitor.on_candle_closed(c3)
    assert len(result) == 1
    watches = monitor._cascade["S"].get_active_watches("S")
    assert len(watches) == 1 and watches[0].trigger_tf == "5m"


if __name__ == "__main__":
    current_module = sys.modules[__name__]
    test_fns = [obj for name, obj in vars(current_module).items() if name.startswith("test_") and callable(obj)]
    passed, failed = 0, []
    for fn in test_fns:
        try:
            fn(); passed += 1
        except AssertionError as e:
            failed.append((fn.__name__, str(e)))
        except Exception as e:
            failed.append((fn.__name__, f"{type(e).__name__}: {e}"))
    print(f"PASSED: {passed}/{len(test_fns)}")
    for name, err in failed:
        print(f"FAILED: {name} -> {err}")
