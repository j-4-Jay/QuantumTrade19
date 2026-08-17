"""File 03.1 deterministic tests for the selectable zone source-TF matrix."""
from __future__ import annotations

from engines.workers.poi.fvg_detector_worker import FVGDetectorWorker
from engines.workers.poi.orderblock_detector_worker import OrderBlockDetectorWorker
from engines.workers.poi.poi_types import DEFAULT_ZONE_SOURCE_TF_ENABLED, POIType
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, candle, flat_candles

SYMBOL = "B-BTC_USDT"


def _bullish_fvg() -> list[dict]:
    return [
        candle(95, 100, 90, 96),
        candle(96, 108, 95, 107),
        candle(107, 115, 110, 114),
    ]


def _bullish_order_block() -> list[dict]:
    rows = flat_candles(15, start=100.0, span=1.0)
    rows.append(candle(100.5, 101.0, 99.0, 99.5))
    rows.append(candle(99.5, 107.5, 99.5, 107.0))
    return rows


def test_default_zone_source_matrix_has_only_1m_and_15m_enabled() -> None:
    assert DEFAULT_ZONE_SOURCE_TF_ENABLED == {
        "1m": True,
        "5m": False,
        "15m": True,
        "1H": False,
        "4H": False,
        "1D": False,
        "1W": False,
        "1M": False,
    }


def test_fvg_scans_only_enabled_source_timeframes() -> None:
    monitor = FakeMarketDataMonitor()
    monitor.set_series("1m", _bullish_fvg())
    monitor.set_series("5m", _bullish_fvg())
    monitor.set_series("15m", _bullish_fvg())
    monitor.set_series("4H", _bullish_fvg())

    matrix = dict(DEFAULT_ZONE_SOURCE_TF_ENABLED)
    worker = FVGDetectorWorker(
        monitor,
        SYMBOL,
        {POIType.FVG: True},
        lambda _symbol, _pois: None,
        zone_source_tf_enabled=matrix,
    )

    assert {poi.source_tf for poi in worker.recompute()} == {"1m", "15m"}
    assert all(call[1] in {"1m", "15m"} for call in monitor.fetch_calls)


def test_fvg_source_tf_can_be_enabled_and_disabled_live() -> None:
    monitor = FakeMarketDataMonitor()
    monitor.set_series("1m", _bullish_fvg())
    monitor.set_series("5m", _bullish_fvg())

    matrix = {tf: False for tf in DEFAULT_ZONE_SOURCE_TF_ENABLED}
    matrix["1m"] = True
    worker = FVGDetectorWorker(
        monitor,
        SYMBOL,
        {POIType.FVG: True},
        lambda _symbol, _pois: None,
        zone_source_tf_enabled=matrix,
    )

    assert {poi.source_tf for poi in worker.recompute()} == {"1m"}
    worker.set_source_tf_enabled("5m", True)
    assert {poi.source_tf for poi in worker.recompute()} == {"1m", "5m"}
    worker.set_source_tf_enabled("1m", False)
    assert {poi.source_tf for poi in worker.recompute()} == {"5m"}


def test_order_blocks_scan_only_enabled_source_timeframes() -> None:
    monitor = FakeMarketDataMonitor()
    monitor.set_series("1m", _bullish_order_block())
    monitor.set_series("5m", _bullish_order_block())
    monitor.set_series("15m", _bullish_order_block())

    matrix = dict(DEFAULT_ZONE_SOURCE_TF_ENABLED)
    worker = OrderBlockDetectorWorker(
        monitor,
        SYMBOL,
        {POIType.ORDER_BLOCK: True},
        lambda _symbol, _pois: None,
        zone_source_tf_enabled=matrix,
    )

    assert {poi.source_tf for poi in worker.recompute()} == {"1m", "15m"}


def test_zone_source_setting_does_not_change_poi_type_strategy_setting() -> None:
    monitor = FakeMarketDataMonitor()
    monitor.set_series("1m", _bullish_fvg())

    strategy = {POIType.FVG: True}
    matrix = {tf: False for tf in DEFAULT_ZONE_SOURCE_TF_ENABLED}
    worker = FVGDetectorWorker(
        monitor,
        SYMBOL,
        strategy,
        lambda _symbol, _pois: None,
        zone_source_tf_enabled=matrix,
        strategy_enabled=strategy,
    )

    assert worker.recompute() == []
    assert strategy[POIType.FVG] is True
    worker.set_source_tf_enabled("1m", True)
    assert len(worker.recompute()) == 1
    assert strategy[POIType.FVG] is True
