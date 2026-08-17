"""Availability probing for all File 03.1 POI source timeframes."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Protocol

from .poi_types import LINE_SOURCE_TFS

logger = logging.getLogger("poi_monitor.htf_availability")


class MarketDataMonitorLike(Protocol):
    """Read-only Market Data Monitor interface consumed by POI workers."""

    def get_live_candle(self, symbol: str, tf: str): ...
    def get_historical_candles(self, symbol: str, tf: str, days: int): ...
    def subscribe(self, symbol: str) -> None: ...
    def get_health(self): ...


MIN_CANDLES_FOR_AVAILABLE: Dict[str, int] = {
    "1m": 2,
    "5m": 2,
    "15m": 2,
    "1H": 2,
    "4H": 2,
    "1D": 2,
    "1W": 2,
    "1M": 2,
}

PROBE_DAYS: Dict[str, int] = {
    "1m": 1,
    "5m": 1,
    "15m": 1,
    "1H": 3,
    "4H": 5,
    "1D": 5,
    "1W": 21,
    "1M": 95,
}


@dataclass
class HTFAvailability:
    populated: Dict[str, bool]
    candle_counts: Dict[str, int]

    def is_available(self, tf: str) -> bool:
        return self.populated.get(tf, False)


def probe_htf_availability(
    market_data_monitor: MarketDataMonitorLike,
    symbol: str,
) -> HTFAvailability:
    """Probe local monitor-served candles without directly calling a broker."""

    populated: Dict[str, bool] = {}
    counts: Dict[str, int] = {}

    for tf in LINE_SOURCE_TFS:
        try:
            candles = market_data_monitor.get_historical_candles(
                symbol,
                tf,
                PROBE_DAYS[tf],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "poi_source_timeframe_probe_failed symbol=%s timeframe=%s error=%s",
                symbol,
                tf,
                exc,
            )
            candles = []

        count = len(candles) if candles else 0
        required = MIN_CANDLES_FOR_AVAILABLE[tf]
        counts[tf] = count
        populated[tf] = count >= required

        if not populated[tf]:
            logger.debug(
                "poi_source_timeframe_not_ready symbol=%s timeframe=%s "
                "candles=%d required=%d",
                symbol,
                tf,
                count,
                required,
            )

    return HTFAvailability(populated=populated, candle_counts=counts)