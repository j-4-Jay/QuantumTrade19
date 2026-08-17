"""File 03.1 previous-completed H/L POI calculator."""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import (
    HTFAvailability,
    MarketDataMonitorLike,
    probe_htf_availability,
)
from .poi_types import (
    DEFAULT_DISPLAY_ENABLED,
    DEFAULT_STRATEGY_ENABLED,
    POI,
    POIType,
    POI_SOURCE_TF,
)

logger = logging.getLogger("poi_monitor.poi_level_calculator_worker")

FRACTAL_LOOKBACK = 2

LOOKBACK_DAYS_FOR_TF: Dict[str, int] = {
    "1m": 1,
    "5m": 1,
    "15m": 1,
    "1H": 3,
    "4H": 5,
    "1D": 5,
    "1W": 21,
    "1M": 95,
}

LINE_MAPPING: Dict[str, tuple[str, str]] = {
    POIType.PREV_1M_HIGH: ("1m", "high"),
    POIType.PREV_1M_LOW: ("1m", "low"),
    POIType.PREV_5M_HIGH: ("5m", "high"),
    POIType.PREV_5M_LOW: ("5m", "low"),
    POIType.PREV_15M_HIGH: ("15m", "high"),
    POIType.PREV_15M_LOW: ("15m", "low"),
    POIType.PREV_1H_HIGH: ("1H", "high"),
    POIType.PREV_1H_LOW: ("1H", "low"),
    POIType.H4_HIGH: ("4H", "high"),
    POIType.H4_LOW: ("4H", "low"),
    POIType.PDH: ("1D", "high"),
    POIType.PDL: ("1D", "low"),
    POIType.WEEK_HIGH: ("1W", "high"),
    POIType.WEEK_LOW: ("1W", "low"),
    POIType.MONTH_HIGH: ("1M", "high"),
    POIType.MONTH_LOW: ("1M", "low"),
}


def _is_swing_high(candles: List, index: int) -> bool:
    if index - FRACTAL_LOOKBACK < 0:
        return False
    if index + FRACTAL_LOOKBACK >= len(candles):
        return False

    high = cf(candles[index], "high")
    return all(
        cf(candles[index - offset], "high") <= high
        and cf(candles[index + offset], "high") <= high
        for offset in range(1, FRACTAL_LOOKBACK + 1)
    )


def _is_swing_low(candles: List, index: int) -> bool:
    if index - FRACTAL_LOOKBACK < 0:
        return False
    if index + FRACTAL_LOOKBACK >= len(candles):
        return False

    low = cf(candles[index], "low")
    return all(
        cf(candles[index - offset], "low") >= low
        and cf(candles[index + offset], "low") >= low
        for offset in range(1, FRACTAL_LOOKBACK + 1)
    )


class POILevelCalculatorWorker:
    """Computes UTC-aligned previous completed H/L lines and flip levels."""

    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        on_poi_update: Callable[[str, List[POI]], None],
        *,
        display_enabled: Optional[Dict[str, bool]] = None,
        strategy_enabled: Optional[Dict[str, bool]] = None,
        zone_source_tf_enabled: Optional[Dict[str, bool]] = None,
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.display_enabled = display_enabled or dict(DEFAULT_DISPLAY_ENABLED)
        self.strategy_enabled = strategy_enabled or enabled_types
        self.zone_source_tf_enabled = zone_source_tf_enabled or {}
        self.on_poi_update = on_poi_update
        self.availability: HTFAvailability = probe_htf_availability(
            market_data_monitor,
            symbol,
        )
        self._last_recompute_ts = 0.0
        self._pois: Dict[str, POI] = {}

    def refresh_availability(self) -> None:
        self.availability = probe_htf_availability(self.mdm, self.symbol)

    def is_type_ready(self, poi_type: str) -> bool:
        if not self.strategy_enabled.get(poi_type, False):
            return False
        source_tf = POI_SOURCE_TF.get(poi_type)
        return source_tf is None or self.availability.is_available(source_tf)

    def _line_poi(
        self,
        poi_type: str,
        price: float,
        source_tf: str,
        formed_at_index: int,
        formed_at_ts: float,
    ) -> POI:
        is_high = poi_type.endswith("_HIGH") or poi_type == POIType.PDH
        return POI(
            poi_id=f"{self.symbol}:{poi_type}",
            symbol=self.symbol,
            poi_type=poi_type,
            role="resistance" if is_high else "support",
            source_tf=source_tf,
            price=price,
            formed_at_index=formed_at_index,
            formed_at_ts=formed_at_ts,
            display_enabled=self.display_enabled.get(poi_type, False),
            strategy_enabled=self.strategy_enabled.get(poi_type, False),
            metadata={
                "source_kind": "previous_completed_futures_candle",
                "broker_boundary": "UTC",
                "source_tf": source_tf,
            },
        )

    def _compute_prev_period_high_low(
        self,
        tf: str,
    ) -> Optional[tuple[float, float, int, float]]:
        """Use index -2 only; index -1 is the forming UTC broker candle."""

        candles = self.mdm.get_historical_candles(
            self.symbol,
            tf,
            LOOKBACK_DAYS_FOR_TF[tf],
        )
        if not candles or len(candles) < 2:
            return None

        previous = candles[-2]
        source_ts = getattr(
            previous,
            "open_time",
            previous.get("open_time", previous.get("bucket_start_ms", 0))
            if isinstance(previous, dict)
            else 0,
        )
        return (
            cf(previous, "high"),
            cf(previous, "low"),
            len(candles) - 2,
            float(source_ts),
        )

    def _compute_line_types(self) -> List[POI]:
        results: List[POI] = []

        for poi_type, (tf, side) in LINE_MAPPING.items():
            if not self.is_type_ready(poi_type):
                continue

            previous = self._compute_prev_period_high_low(tf)
            if previous is None:
                continue

            high, low, index, source_ts = previous
            results.append(
                self._line_poi(
                    poi_type=poi_type,
                    price=high if side == "high" else low,
                    source_tf=tf,
                    formed_at_index=index,
                    formed_at_ts=source_ts,
                )
            )

        return results

    def _compute_flip_types(self) -> List[POI]:
        """Flip detection is source-TF-matrix aware in the next patch batch."""

        return []

    def recompute(self) -> List[POI]:
        pois = self._compute_line_types() + self._compute_flip_types()
        self._pois = {poi.poi_id: poi for poi in pois}
        self._last_recompute_ts = time.time()
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_type_enabled(self, poi_type: str, enabled: bool) -> None:
        """Legacy API: controls strategy eligibility."""

        self.strategy_enabled[poi_type] = bool(enabled)
        self.enabled_types[poi_type] = bool(enabled)
        self.recompute()

    def set_display_enabled(self, poi_type: str, enabled: bool) -> None:
        """Rendering-only setting; does not affect strategy eligibility."""

        self.display_enabled[poi_type] = bool(enabled)
        self.recompute()

    async def run_forever(self, poll_seconds: float = 30.0) -> None:
        import asyncio

        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "poi_level_calculator_worker_failed symbol=%s",
                    self.symbol,
                )
            await asyncio.sleep(poll_seconds)