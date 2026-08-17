"""Deterministic File 03 / File 03.1 checks for InverseFVGDetectorWorker."""
from __future__ import annotations

from engines.workers.poi.inverse_fvg_detector_worker import InverseFVGDetectorWorker
from engines.workers.poi.poi_types import POI, POIType
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, candle

SYMBOL = "B-BTC_USDT"


def _fvg(poi_id: str, role: str, low: float = 100.0, high: float = 110.0) -> POI:
    return POI(
        poi_id=poi_id, symbol=SYMBOL, poi_type=POIType.FVG, role=role,
        source_tf="4H", price_low=low, price_high=high, formed_at_index=7,
        metadata={"direction": "bullish" if role == "support" else "bearish"},
    )


def _worker(mdm: FakeMarketDataMonitor, fvgs: list[POI], enabled: bool = True):
    updates = []
    worker = InverseFVGDetectorWorker(
        mdm, SYMBOL, {POIType.INVERSE_FVG: enabled},
        get_fvg_pois=lambda: list(fvgs),
        on_poi_update=lambda symbol, pois: updates.append((symbol, list(pois))),
    )
    return worker, updates


def test_first_close_through_records_breach_but_does_not_create_inverse_fvg():
    mdm = FakeMarketDataMonitor()
    mdm.set_live("4H", candle(109, 115, 108, 112))
    worker, updates = _worker(mdm, [_fvg("bull-gap", "support")])
    assert worker.recompute() == []
    assert worker._first_close_through == {"bull-gap": "up"}
    assert updates[-1] == (SYMBOL, [])


def test_second_opposite_close_through_creates_inverse_fvg_and_flips_role():
    mdm = FakeMarketDataMonitor()
    worker, _ = _worker(mdm, [_fvg("bull-gap", "support")])
    mdm.set_live("4H", candle(109, 115, 108, 112))
    assert worker.recompute() == []
    mdm.set_live("4H", candle(101, 102, 95, 98))
    pois = worker.recompute()
    assert len(pois) == 1
    inverse = pois[0]
    assert inverse.poi_id == "bull-gap:inverse"
    assert inverse.poi_type == POIType.INVERSE_FVG
    assert inverse.role == "resistance"
    assert inverse.source_tf == "4H"
    assert inverse.price_low == 100.0
    assert inverse.price_high == 110.0
    assert inverse.formed_at_index == 7
    assert inverse.metadata["original_fvg_id"] == "bull-gap"
    assert inverse.metadata["original_role"] == "support"
    assert inverse.metadata["source_tf"] == "4H"
    assert inverse.metadata["broker_boundary"] == "UTC"


def test_bearish_fvg_flips_from_resistance_to_support_after_down_then_up_breaches():
    mdm = FakeMarketDataMonitor()
    worker, _ = _worker(mdm, [_fvg("bear-gap", "resistance")])
    mdm.set_live("4H", candle(101, 102, 95, 98))
    assert worker.recompute() == []
    mdm.set_live("4H", candle(109, 115, 108, 112))
    pois = worker.recompute()
    assert len(pois) == 1
    assert pois[0].role == "support"
    assert pois[0].metadata["original_role"] == "resistance"


def test_same_direction_multiple_breaches_never_confirm_flip():
    mdm = FakeMarketDataMonitor()
    worker, _ = _worker(mdm, [_fvg("same-direction", "support")])
    mdm.set_live("4H", candle(109, 115, 108, 112))
    assert worker.recompute() == []
    mdm.set_live("4H", candle(111, 116, 110, 113))
    assert worker.recompute() == []
    assert worker._pois == {}
    assert worker._first_close_through["same-direction"] == "up"


def test_no_breach_inside_range_creates_nothing():
    mdm = FakeMarketDataMonitor()
    mdm.set_live("4H", candle(103, 108, 102, 106))
    worker, _ = _worker(mdm, [_fvg("inside", "support")])
    assert worker.recompute() == []
    assert worker._first_close_through == {}


def test_consumes_injected_fvg_output_and_ignores_other_symbol_pois():
    mdm = FakeMarketDataMonitor()
    mdm.set_live("4H", candle(109, 115, 108, 112))
    other = POI(poi_id="other-gap", symbol="B-ETH_USDT", poi_type=POIType.FVG,
                role="support", source_tf="4H", price_low=100, price_high=110)
    worker, _ = _worker(mdm, [_fvg("own-gap", "support"), other])
    assert worker.recompute() == []
    assert worker._first_close_through == {"own-gap": "up"}


def test_toggle_off_clears_inverses_and_does_not_evaluate_breaches():
    mdm = FakeMarketDataMonitor()
    mdm.set_live("4H", candle(109, 115, 108, 112))
    worker, updates = _worker(mdm, [_fvg("off-gap", "support")], enabled=False)
    assert worker.recompute() == []
    assert worker._first_close_through == {}
    assert updates[-1] == (SYMBOL, [])
    worker.set_enabled(True)
    assert worker._first_close_through == {"off-gap": "up"}
