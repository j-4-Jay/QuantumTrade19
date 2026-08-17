"""
tests/workers/poi/test_poi_monitor_check_gates.py

Standalone, fully-mocked test harness for File 03's check gates (no live
CoinDCX calls — per Standing Suggestion: every Worker check gate includes at
least one fabricated/mocked-data test). Covers, in order:

1. Settings toggle turns a POI type's calculation on/off live.
2. PDH/PDL and 4H H/L (default-ON types) compute correctly against a known
   fabricated historical example.
3. State tags transition Approaching -> Hit -> Crossed -> Retesting along a
   simulated price path.
4. Multiple POIs on the same symbol track fully independently.

NOTE on fixture sizing: htf_availability.py requires a *minimum* candle
count per TF before treating it as "populated" (mirrors how a real,
freshly-activated symbol wouldn't have a full HTF history yet either).
The 4H fixture below intentionally carries >= MIN_CANDLES_FOR_AVAILABLE["4H"]
(6) candles so the availability probe passes and 4H_HIGH/4H_LOW actually
compute — with too few candles, POI_Level_Calculator_Worker is *supposed*
to leave that type unresolved rather than compute off thin data.

Run with: pytest tests/workers/poi/test_poi_monitor_check_gates.py -v
"""
from __future__ import annotations

from typing import Dict, List

import pytest

from engines.workers.poi.poi_types import POI, POIType, POIState
from engines.workers.poi.poi_level_calculator_worker import POILevelCalculatorWorker
from engines.workers.poi.poi_state_tracker_worker import POIStateTrackerWorker


class FakeMarketDataMonitor:
    """Duck-types get_live_candle/get_historical_candles/subscribe/get_health
    exactly as documented for Market_Data_Monitor's Tier-2 interface."""

    def __init__(self) -> None:
        self.series: Dict[str, List[dict]] = {}
        self.live: Dict[str, dict] = {}

    def set_series(self, tf: str, candles: List[dict]) -> None:
        self.series[tf] = candles

    def set_live(self, tf: str, candle: dict) -> None:
        self.live[tf] = candle

    def get_historical_candles(self, symbol: str, tf: str, days: int) -> List[dict]:
        return self.series.get(tf, [])

    def get_live_candle(self, symbol: str, tf: str):
        return self.live.get(tf)

    def subscribe(self, symbol: str) -> None:
        pass

    def get_health(self) -> str:
        return "OK"


def _mk_candle(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


@pytest.fixture
def mdm() -> FakeMarketDataMonitor:
    m = FakeMarketDataMonitor()

    # 1D series: yesterday (completed, index -2) high=105 low=95, today
    # (forming, index -1) must be ignored. 3 candles clears the 1D minimum (2).
    m.set_series("1D", [
        _mk_candle(100, 102, 98, 101),
        _mk_candle(101, 105, 95, 100),   # <- completed "yesterday", PDH=105 PDL=95
        _mk_candle(100, 103, 99, 102),   # <- forming "today", must be ignored
    ])

    # 4H series: 7 candles total, clearing the 4H availability minimum (6).
    # index -2 is the most recently *completed* 4H candle: high=112 low=108.
    # index -1 is the still-forming candle and must be ignored.
    m.set_series("4H", [
        _mk_candle(105, 107, 103, 106),
        _mk_candle(106, 108, 104, 107),
        _mk_candle(107, 109, 105, 108),
        _mk_candle(108, 110, 106, 109),
        _mk_candle(109, 111, 107, 110),
        _mk_candle(109, 112, 108, 111),  # <- completed, 4H_HIGH=112 4H_LOW=108
        _mk_candle(111, 113, 110, 112),  # <- forming, ignored
    ])
    m.set_live("1H", {"close": 100.0})
    return m


def test_type_toggle_turns_calculation_on_off_live(mdm):
    enabled = {POIType.PDH: True, POIType.PDL: True, POIType.H4_HIGH: True, POIType.H4_LOW: True}
    calc = POILevelCalculatorWorker(mdm, "BTCUSDT", enabled, lambda s, p: None)
    pois = calc.recompute()
    assert any(p.poi_type == POIType.PDH for p in pois)

    calc.set_type_enabled(POIType.PDH, False)
    pois_after = calc.recompute()
    assert not any(p.poi_type == POIType.PDH for p in pois_after)

    calc.set_type_enabled(POIType.PDH, True)
    pois_reenabled = calc.recompute()
    assert any(p.poi_type == POIType.PDH for p in pois_reenabled)


def test_pdh_pdl_and_4h_hl_known_example(mdm):
    enabled = {POIType.PDH: True, POIType.PDL: True, POIType.H4_HIGH: True, POIType.H4_LOW: True}
    calc = POILevelCalculatorWorker(mdm, "BTCUSDT", enabled, lambda s, p: None)
    pois = {p.poi_type: p.price for p in calc.recompute()}

    assert pois[POIType.PDH] == 105
    assert pois[POIType.PDL] == 95
    assert pois[POIType.H4_HIGH] == 112
    assert pois[POIType.H4_LOW] == 108


def test_state_transitions_along_simulated_price_path(mdm):
    tick_size = 1.0
    poi = POI(poi_id="X:PDH", symbol="BTCUSDT", poi_type=POIType.PDH,
              role="resistance", source_tf="1D", price=105.0)
    tracker = POIStateTrackerWorker(
        mdm, "BTCUSDT", tick_size, get_active_pois=lambda: [poi], on_state_update=lambda s, r: None)

    # Approaching: far below the level.
    r = tracker.update_one(poi, 100.0, now=1)
    assert r.state == POIState.APPROACHING

    # Hit: within touch epsilon.
    r = tracker.update_one(poi, 104.6, now=2)
    assert r.state == POIState.HIT
    assert r.last_touch_ts == 2

    # Crossed: closes fully through to the other side.
    r = tracker.update_one(poi, 110.0, now=3)
    assert r.state == POIState.CROSSED
    assert r.crossed_direction == "above"

    # Retesting: comes back near the level from the far side.
    r = tracker.update_one(poi, 105.5, now=4)
    assert r.state == POIState.RETESTING
    assert r.last_touch_ts == 4


def test_multiple_pois_track_independently():
    mdm = FakeMarketDataMonitor()
    poi_a = POI(poi_id="A", symbol="BTCUSDT", poi_type=POIType.PDH, role="resistance",
                source_tf="1D", price=100.0)
    poi_b = POI(poi_id="B", symbol="BTCUSDT", poi_type=POIType.PDL, role="support",
                source_tf="1D", price=50.0)
    tracker = POIStateTrackerWorker(
        mdm, "BTCUSDT", 1.0, get_active_pois=lambda: [poi_a, poi_b], on_state_update=lambda s, r: None)

    tracker.update_one(poi_a, 99.6, now=1)   # touches A
    tracker.update_one(poi_b, 200.0, now=1)  # B stays far away, approaching only

    state_a = tracker._states["A"]
    state_b = tracker._states["B"]
    assert state_a.state == POIState.HIT
    assert state_b.state == POIState.APPROACHING

    # Moving A further should never change B's stored state.
    tracker.update_one(poi_a, 110.0, now=2)
    assert tracker._states["B"] is state_b
    assert tracker._states["B"].state == POIState.APPROACHING
