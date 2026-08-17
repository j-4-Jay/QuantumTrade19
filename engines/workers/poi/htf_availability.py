"""
engines/workers/poi/htf_availability.py

Resolves the OPEN DECISION from the File 03 continuation prompt: rather than
hardcoding the assumption that all of 1H/4H/1D/1W/1M are populated by
Candle_Builder_Worker, every POI Monitor Worker probes Market_Data_Monitor
live at startup and treats missing/thin series as gracefully degraded
(type disabled + logged), not a crash.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Protocol

from .poi_types import POI_TFS

logger = logging.getLogger("poi_monitor.htf_availability")


class MarketDataMonitorLike(Protocol):
    def get_live_candle(self, symbol: str, tf: str) -> dict | None: ...
    def get_historical_candles(self, symbol: str, tf: str, days: int) -> list[dict]: ...
    def subscribe(self, symbol: str) -> None: ...
    def get_health(self) -> str: ...


MIN_CANDLES_FOR_AVAILABLE = {
    "1H": 24,   # >= 1 day worth
    "4H": 6,    # >= 1 day worth
    "1D": 2,    # >= 2 completed days
    "1W": 1,    # >= 1 completed week
    "1M": 1,    # >= 1 completed month
}

PROBE_DAYS = {"1H": 3, "4H": 7, "1D": 10, "1W": 30, "1M": 90}


@dataclass
class HTFAvailability:
    populated: Dict[str, bool]
    candle_counts: Dict[str, int]

    def is_available(self, tf: str) -> bool:
        return self.populated.get(tf, False)


def probe_htf_availability(market_data_monitor: MarketDataMonitorLike, symbol: str) -> HTFAvailability:
    """Call once per symbol on Worker startup, and re-call on a slow interval
    (e.g. every 10 min) in case Candle_Builder_Worker backfills a TF later."""
    populated: Dict[str, bool] = {}
    counts: Dict[str, int] = {}

    for tf in POI_TFS:
        try:
            candles = market_data_monitor.get_historical_candles(symbol, tf, PROBE_DAYS.get(tf, 7))
        except Exception as exc:  # noqa: BLE001 - probe must never raise
            logger.warning("HTF probe failed for %s/%s: %s", symbol, tf, exc)
            candles = []

        count = len(candles) if candles else 0
        counts[tf] = count
        populated[tf] = count >= MIN_CANDLES_FOR_AVAILABLE.get(tf, 1)

        if not populated[tf]:
            logger.warning(
                "HTF timeframe %s not yet populated for %s (%d candles seen, "
                "need >=%d). POI types sourced from %s stay disabled until it fills.",
                tf, symbol, count, MIN_CANDLES_FOR_AVAILABLE.get(tf, 1), tf,
            )

    return HTFAvailability(populated=populated, candle_counts=counts)
