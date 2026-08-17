"""
FULL PATH: tests/workers/poi/test_orderblock_detector_worker.py (NEW FILE)

Deterministic check-gate coverage for File 03 Tier 1 Worker #3:
OrderBlock_Detector_Worker.

Run:
    pytest tests/workers/poi/test_orderblock_detector_worker.py -v
"""
from __future__ import annotations

from engines.workers.poi.orderblock_detector_worker import OrderBlockDetectorWorker
from engines.workers.poi.poi_types import POIType
from tests.workers.poi.poi_test_helpers import DETECTOR_SCAN_TFS, FakeMarketDataMonitor, candle, flat_candles

SYMBOL = "B-BTC_USDT"


def _worker(mdm: FakeMarketDataMonitor, enabled: bool = True):
    updates = []
    worker = OrderBlockDetectorWorker(
        mdm, SYMBOL, {POIType.ORDER_BLOCK: enabled},
        on_poi_update=lambda symbol, pois: updates.append((symbol, list(pois))),
    )
    return worker, updates


def _set_other_detector_tfs_empty(mdm: FakeMarketDataMonitor) -> None:
    for tf in ("1D", "1W", "1M"):
        mdm.set_series(tf, [])


def test_bullish_order_block_is_last_red_candle_before_strong_green_impulse():
    mdm = FakeMarketDataMonitor()
    rows = flat_candles(15, start=100.0, span=1.0)
    # Index 15 is the final opposite-colored (red) candle, range [99, 101].
    rows.append(candle(100.5, 101.0, 99.0, 99.5))
    # Index 16 is a strong green impulse: range 8 >> prior ATR around 2.
    rows.append(candle(99.5, 107.5, 99.5, 107.0))
    mdm.set_series("4H", rows)
    _set_other_detector_tfs_empty(mdm)

    worker, _ = _worker(mdm)
    pois = worker.recompute()

    assert len(pois) == 1
    poi = pois[0]
    assert poi.poi_type == POIType.ORDER_BLOCK
    assert poi.role == "support"
    assert poi.source_tf == "4H"
    assert poi.price_low == 99.0
    assert poi.price_high == 101.0
    assert poi.formed_at_index == 15
    assert poi.metadata["impulse_index"] == 16
    assert poi.metadata["range"] == 8.0
    assert poi.poi_id == f"{SYMBOL}:OB:4H:16:bull"


def test_bearish_order_block_is_last_green_candle_before_strong_red_impulse():
    mdm = FakeMarketDataMonitor()
    rows = flat_candles(15, start=100.0, span=1.0)
    # Index 15 is the final opposite-colored (green) candle, range [99, 101].
    rows.append(candle(99.5, 101.0, 99.0, 100.5))
    # Index 16 is a strong red impulse.
    rows.append(candle(100.5, 100.5, 92.5, 93.0))
    mdm.set_series("4H", rows)
    _set_other_detector_tfs_empty(mdm)

    worker, _ = _worker(mdm)
    pois = worker.recompute()

    assert len(pois) == 1
    poi = pois[0]
    assert poi.role == "resistance"
    assert poi.price_low == 99.0
    assert poi.price_high == 101.0
    assert poi.formed_at_index == 15
    assert poi.metadata["impulse_index"] == 16
    assert poi.metadata["range"] == 8.0
    assert poi.poi_id == f"{SYMBOL}:OB:4H:16:bear"


def test_non_impulsive_move_creates_no_order_block():
    mdm = FakeMarketDataMonitor()
    # All ranges remain ~2, so none can be 1.8x the rolling ATR.
    mdm.set_series("4H", flat_candles(20, start=100.0, span=1.0))
    _set_other_detector_tfs_empty(mdm)

    worker, _ = _worker(mdm)
    assert worker.recompute() == []


def test_requires_at_least_atr_window_plus_two_candles():
    mdm = FakeMarketDataMonitor()
    mdm.set_series("4H", flat_candles(15))  # Worker threshold is 16 candles.
    _set_other_detector_tfs_empty(mdm)

    worker, _ = _worker(mdm)
    assert worker.recompute() == []


def test_toggle_off_clears_order_blocks_live_and_toggle_on_recomputes():
    mdm = FakeMarketDataMonitor()
    rows = flat_candles(15, start=100.0, span=1.0)
    rows.append(candle(100.5, 101.0, 99.0, 99.5))
    rows.append(candle(99.5, 107.5, 99.5, 107.0))
    mdm.set_series("4H", rows)
    _set_other_detector_tfs_empty(mdm)

    worker, updates = _worker(mdm, enabled=True)
    assert len(worker.recompute()) == 1

    worker.set_enabled(False)
    assert worker._pois == {}
    assert updates[-1] == (SYMBOL, [])

    worker.set_enabled(True)
    assert len(worker._pois) == 1
    assert len(updates[-1][1]) == 1
