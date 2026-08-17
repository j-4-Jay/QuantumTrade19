"""
FULL PATH: tests/workers/poi/test_fvg_detector_worker.py (NEW FILE)

Deterministic check-gate coverage for File 03 Tier 1 Worker #2:
FVG_Detector_Worker.

Run:
    pytest tests/workers/poi/test_fvg_detector_worker.py -v
"""
from __future__ import annotations

from engines.workers.poi.fvg_detector_worker import FVGDetectorWorker
from engines.workers.poi.poi_types import POIType
from tests.workers.poi.poi_test_helpers import DETECTOR_SCAN_TFS, FakeMarketDataMonitor, candle

SYMBOL = "B-BTC_USDT"


def _worker(mdm: FakeMarketDataMonitor, enabled: bool = True):
    updates = []
    worker = FVGDetectorWorker(
        mdm, SYMBOL, {POIType.FVG: enabled},
        on_poi_update=lambda symbol, pois: updates.append((symbol, list(pois))),
    )
    return worker, updates


def test_bullish_fvg_records_support_range_and_formation_index():
    mdm = FakeMarketDataMonitor()
    # c3.low=110 > c1.high=100, leaving bullish FVG [100, 110].
    mdm.set_series("4H", [
        candle(95, 100, 90, 96),
        candle(96, 108, 95, 107),
        candle(107, 115, 110, 114),
    ])
    for tf in ("1D", "1W", "1M"):
        mdm.set_series(tf, [])

    worker, updates = _worker(mdm)
    pois = worker.recompute()

    assert len(pois) == 1
    poi = pois[0]
    assert poi.poi_type == POIType.FVG
    assert poi.role == "support"
    assert poi.source_tf == "4H"
    assert poi.price_low == 100
    assert poi.price_high == 110
    assert poi.formed_at_index == 2
    assert poi.metadata == {"direction": "bullish", "impulse_candle_index": 1}
    assert poi.poi_id == f"{SYMBOL}:FVG:4H:2:bull"
    assert updates[-1][0] == SYMBOL
    assert updates[-1][1] == pois


def test_bearish_fvg_records_resistance_range_and_formation_index():
    mdm = FakeMarketDataMonitor()
    # c3.high=90 < c1.low=100, leaving bearish FVG [90, 100].
    mdm.set_series("4H", [
        candle(105, 110, 100, 104),
        candle(104, 106, 95, 96),
        candle(96, 90, 80, 82),
    ])
    for tf in ("1D", "1W", "1M"):
        mdm.set_series(tf, [])

    worker, _ = _worker(mdm)
    pois = worker.recompute()

    assert len(pois) == 1
    poi = pois[0]
    assert poi.role == "resistance"
    assert poi.price_low == 90
    assert poi.price_high == 100
    assert poi.formed_at_index == 2
    assert poi.metadata == {"direction": "bearish", "impulse_candle_index": 1}
    assert poi.poi_id == f"{SYMBOL}:FVG:4H:2:bear"


def test_touching_boundaries_is_not_an_fvg():
    mdm = FakeMarketDataMonitor()
    # Strict inequality is intentional: c3.low == c1.high is a touch, no gap.
    mdm.set_series("4H", [
        candle(95, 100, 90, 96),
        candle(96, 105, 95, 104),
        candle(104, 110, 100, 108),
    ])
    for tf in ("1D", "1W", "1M"):
        mdm.set_series(tf, [])

    worker, _ = _worker(mdm)
    assert worker.recompute() == []


def test_scans_each_htf_independently_without_cross_tf_leakage():
    mdm = FakeMarketDataMonitor()
    bullish = [
        candle(95, 100, 90, 96), candle(96, 108, 95, 107), candle(107, 115, 110, 114),
    ]
    bearish = [
        candle(105, 110, 100, 104), candle(104, 106, 95, 96), candle(96, 90, 80, 82),
    ]
    mdm.set_series("4H", bullish)
    mdm.set_series("1D", bearish)
    mdm.set_series("1W", [])
    mdm.set_series("1M", [])

    worker, _ = _worker(mdm)
    pois = worker.recompute()

    assert {(p.source_tf, p.role) for p in pois} == {("4H", "support"), ("1D", "resistance")}


def test_toggle_off_clears_pois_live_and_toggle_on_recomputes_them():
    mdm = FakeMarketDataMonitor()
    mdm.set_series("4H", [
        candle(95, 100, 90, 96), candle(96, 108, 95, 107), candle(107, 115, 110, 114),
    ])
    for tf in ("1D", "1W", "1M"):
        mdm.set_series(tf, [])

    worker, updates = _worker(mdm, enabled=True)
    assert len(worker.recompute()) == 1

    worker.set_enabled(False)
    assert worker._pois == {}
    assert updates[-1] == (SYMBOL, [])

    worker.set_enabled(True)
    assert len(worker._pois) == 1
    assert updates[-1][0] == SYMBOL
    assert len(updates[-1][1]) == 1
