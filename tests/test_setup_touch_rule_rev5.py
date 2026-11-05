"""
FULL PATH: tests/test_setup_touch_rule_rev5.py
File 04 REVISION 5 (Jay, 05-11-2026): a Candle1/Candle2 pairing is valid when Candle 1
and/or Candle 2 touched the POI (either one, or both). Same rule for Bull and Bear.
"""
from __future__ import annotations
import sys, os
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.workers.setup.bear123_fsm_worker import Bear123FSMWorker
from engines.workers.setup.bull123_fsm_worker import Bull123FSMWorker
from engines.workers.setup.candle_lock_registry import CandleLockRegistry


@dataclass
class Candle:
    symbol: str
    timeframe: str
    open_time: int
    open: float
    high: float
    low: float
    close: float


def C(t, o, h, l, c):
    return Candle("S", "1m", t, o, h, l, c)


TOUCH = {"poi": None}


def test_bull_jay_live_case_red_touch_then_two_greens_confirms():
    fsm = Bull123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(1, 100.0, 101.0, 99.5, 100.8), {})
    fsm.on_candle_closed(C(2, 100.8, 107.0, 100.5, 106.0), TOUCH)
    fsm.on_candle_closed(C(3, 106.0, 107.0, 104.0, 105.0), TOUCH)
    assert fsm.on_candle_closed(C(4, 105.0, 106.0, 104.8, 105.8), {}) == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 3 and pending[0].c2.open_time == 4
    r = fsm.on_candle_closed(C(5, 105.8, 108.0, 105.7, 107.5), {})
    assert len(r) == 1 and (r[0].c1.open_time, r[0].c2.open_time, r[0].c3.open_time) == (3, 4, 5)


def test_bear_mirror_green_touch_then_two_reds_confirms():
    fsm = Bear123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(1, 100.0, 100.5, 99.0, 99.2), {})
    fsm.on_candle_closed(C(2, 99.2, 99.5, 93.0, 94.0), TOUCH)
    fsm.on_candle_closed(C(3, 94.0, 96.0, 93.0, 95.0), TOUCH)
    assert fsm.on_candle_closed(C(4, 95.0, 95.2, 94.0, 94.2), {}) == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 3 and pending[0].c2.open_time == 4
    r = fsm.on_candle_closed(C(5, 94.2, 94.3, 92.0, 92.5), {})
    assert len(r) == 1 and (r[0].c1.open_time, r[0].c2.open_time, r[0].c3.open_time) == (3, 4, 5)
    assert r[0].direction == Bear123FSMWorker.direction


def test_bull_recycled_anchor_that_touched_pairs_with_untouched_candle():
    fsm = Bull123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(120, 100, 101, 95, 96), {})
    fsm.on_candle_closed(C(121, 96, 105, 95, 104), TOUCH)
    assert fsm.on_candle_closed(C(122, 104, 104, 90, 91), {}) == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 121 and pending[0].c2.open_time == 122


def test_bear_recycled_anchor_that_touched_pairs_with_untouched_candle():
    fsm = Bear123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(120, 100, 105, 99, 104), {})
    fsm.on_candle_closed(C(121, 104, 105, 90, 92), TOUCH)
    assert fsm.on_candle_closed(C(122, 92, 110, 91, 108), {}) == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 121 and pending[0].c2.open_time == 122


def test_bull_untouched_anchor_and_untouched_candle_still_abort_no_drift():
    fsm = Bull123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(10, 100, 101, 95, 96), TOUCH)
    fsm.on_candle_closed(C(11, 96, 105, 95, 104), {})
    assert fsm.on_candle_closed(C(12, 104, 104, 90, 91), {}) == []
    assert fsm.get_pending("S", "1m") == []


def test_bear_untouched_anchor_and_untouched_candle_still_abort_no_drift():
    fsm = Bear123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(10, 100, 105, 99, 104), TOUCH)
    fsm.on_candle_closed(C(11, 104, 105, 90, 92), {})
    assert fsm.on_candle_closed(C(12, 92, 110, 91, 108), {}) == []
    assert fsm.get_pending("S", "1m") == []


def test_untouched_anchor_pairs_again_when_the_next_candle_touches():
    fsm = Bull123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(10, 100, 101, 95, 96), TOUCH)
    fsm.on_candle_closed(C(11, 96, 105, 95, 104), {})
    assert fsm.on_candle_closed(C(12, 104, 104, 90, 91), TOUCH) == []
    pending = fsm.get_pending("S", "1m")
    assert len(pending) == 1 and pending[0].c1.open_time == 11 and pending[0].c2.open_time == 12


def test_doji_after_failed_c3_keeps_anchor_only_if_it_touched():
    touched = Bull123FSMWorker(CandleLockRegistry())
    touched.on_candle_closed(C(1, 100, 101, 95, 96), {})
    touched.on_candle_closed(C(2, 96, 105, 95, 104), TOUCH)
    touched.on_candle_closed(C(3, 104, 105, 103, 104), {})
    p = touched.get_pending("S", "1m")
    assert len(p) == 1 and p[0].stage == "ANCHOR" and p[0].c1.open_time == 2

    untouched = Bull123FSMWorker(CandleLockRegistry())
    untouched.on_candle_closed(C(1, 100, 101, 95, 96), TOUCH)
    untouched.on_candle_closed(C(2, 96, 105, 95, 104), {})
    untouched.on_candle_closed(C(3, 104, 105, 103, 104), {})
    assert untouched.get_pending("S", "1m") == []


def test_chain_never_drifts_more_than_one_untouched_pairing():
    fsm = Bull123FSMWorker(CandleLockRegistry())
    fsm.on_candle_closed(C(1, 100, 101, 95, 96), {})
    fsm.on_candle_closed(C(2, 96, 105, 95, 104), TOUCH)
    fsm.on_candle_closed(C(3, 104, 104, 90, 91), {})
    pending = fsm.get_pending("S", "1m")
    assert pending[0].c1.open_time == 2 and pending[0].c2.open_time == 3
    fsm.on_candle_closed(C(4, 91, 92, 88, 89), {})
    assert fsm.get_pending("S", "1m") == []
