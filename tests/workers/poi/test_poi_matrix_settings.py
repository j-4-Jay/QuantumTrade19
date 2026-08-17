"""Deterministic File 03.1 tests for previous H/L lines and settings."""
from __future__ import annotations

import pytest

from engines.workers.poi.poi_level_calculator_worker import (
    POILevelCalculatorWorker,
)
from engines.workers.poi.poi_settings import POISettings
from engines.workers.poi.poi_types import (
    DEFAULT_DISPLAY_ENABLED,
    DEFAULT_STRATEGY_ENABLED,
    DEFAULT_ZONE_SOURCE_TF_ENABLED,
    POIType,
)
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, candle


LINE_CASES = (
    ("1m", POIType.PREV_1M_HIGH, POIType.PREV_1M_LOW),
    ("5m", POIType.PREV_5M_HIGH, POIType.PREV_5M_LOW),
    ("15m", POIType.PREV_15M_HIGH, POIType.PREV_15M_LOW),
    ("1H", POIType.PREV_1H_HIGH, POIType.PREV_1H_LOW),
    ("4H", POIType.H4_HIGH, POIType.H4_LOW),
    ("1D", POIType.PDH, POIType.PDL),
    ("1W", POIType.WEEK_HIGH, POIType.WEEK_LOW),
    ("1M", POIType.MONTH_HIGH, POIType.MONTH_LOW),
)


def _build_monitor() -> FakeMarketDataMonitor:
    monitor = FakeMarketDataMonitor()

    for index, (timeframe, _, _) in enumerate(LINE_CASES, start=1):
        completed_high = 1000.0 + index
        completed_low = 900.0 + index
        monitor.set_series(
            timeframe,
            [
                candle(950, 960, 940, 955),
                candle(955, completed_high, completed_low, 950),
                candle(950, completed_high + 20, completed_low - 20, 960),
            ],
        )

    return monitor


def _calculator(
    monitor: FakeMarketDataMonitor,
    strategy_enabled: dict[str, bool] | None = None,
    display_enabled: dict[str, bool] | None = None,
) -> POILevelCalculatorWorker:
    strategy = dict(DEFAULT_STRATEGY_ENABLED)
    if strategy_enabled:
        strategy.update(strategy_enabled)

    display = dict(DEFAULT_DISPLAY_ENABLED)
    if display_enabled:
        display.update(display_enabled)

    return POILevelCalculatorWorker(
        monitor,
        "B-BTC_USDT",
        strategy,
        lambda _symbol, _pois: None,
        display_enabled=display,
        strategy_enabled=strategy,
    )


@pytest.mark.parametrize("timeframe,high_type,low_type", LINE_CASES)
def test_previous_completed_high_low_all_eight_timeframes(
    timeframe: str,
    high_type: str,
    low_type: str,
) -> None:
    monitor = _build_monitor()
    calculator = _calculator(
        monitor,
        strategy_enabled={high_type: True, low_type: True},
    )

    pois = {poi.poi_type: poi for poi in calculator.recompute()}
    case_index = [case[0] for case in LINE_CASES].index(timeframe) + 1

    assert pois[high_type].price == 1000.0 + case_index
    assert pois[low_type].price == 900.0 + case_index
    assert pois[high_type].source_tf == timeframe
    assert pois[low_type].source_tf == timeframe
    assert pois[high_type].formed_at_index == 1
    assert pois[low_type].formed_at_index == 1


@pytest.mark.parametrize("timeframe,high_type,low_type", LINE_CASES)
def test_current_forming_candle_is_excluded(
    timeframe: str,
    high_type: str,
    low_type: str,
) -> None:
    monitor = _build_monitor()
    calculator = _calculator(
        monitor,
        strategy_enabled={high_type: True, low_type: True},
    )

    pois = {poi.poi_type: poi for poi in calculator.recompute()}

    assert pois[high_type].price != 1020.0
    assert pois[low_type].price != 880.0


def test_display_and_strategy_are_independent() -> None:
    monitor = _build_monitor()
    calculator = _calculator(
        monitor,
        strategy_enabled={POIType.PDH: True},
        display_enabled={POIType.PDH: False},
    )

    pdh = next(
        poi
        for poi in calculator.recompute()
        if poi.poi_type == POIType.PDH
    )
    assert pdh.strategy_enabled is True
    assert pdh.display_enabled is False

    calculator.set_display_enabled(POIType.PDH, True)
    pdh = next(
        poi
        for poi in calculator.recompute()
        if poi.poi_type == POIType.PDH
    )
    assert pdh.strategy_enabled is True
    assert pdh.display_enabled is True


def test_file_03_1_default_settings() -> None:
    settings = POISettings()

    assert settings.strategy_enabled[POIType.PDH] is True
    assert settings.strategy_enabled[POIType.PDL] is True
    assert settings.strategy_enabled[POIType.H4_HIGH] is True
    assert settings.strategy_enabled[POIType.H4_LOW] is True
    assert settings.strategy_enabled[POIType.PREV_1M_HIGH] is False
    assert settings.strategy_enabled[POIType.FVG] is False

    assert settings.display_enabled[POIType.PDH] is True
    assert settings.display_enabled[POIType.PDL] is True
    assert settings.display_enabled[POIType.H4_HIGH] is True
    assert settings.display_enabled[POIType.H4_LOW] is True
    assert settings.display_enabled[POIType.WEEK_HIGH] is True
    assert settings.display_enabled[POIType.MONTH_HIGH] is True

    assert settings.zone_source_tf_enabled == DEFAULT_ZONE_SOURCE_TF_ENABLED