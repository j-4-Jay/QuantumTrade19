"""File 03.1 previous-completed H/L and selected-source Flip POI calculator."""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import HTFAvailability, MarketDataMonitorLike, probe_htf_availability
from .poi_types import DEFAULT_DISPLAY_ENABLED, DEFAULT_STRATEGY_ENABLED, POI, POIType, POI_SOURCE_TF, ZONE_SOURCE_TFS

logger = logging.getLogger("poi_monitor.poi_level_calculator_worker")

FRACTAL_LOOKBACK = 2
LEGACY_FLIP_TF = "4H"
LOOKBACK_DAYS_FOR_TF: Dict[str, int] = {
    "1m": 1, "5m": 1, "15m": 1, "1H": 3, "4H": 5, "1D": 5, "1W": 21, "1M": 95,
}
LINE_MAPPING: Dict[str, tuple[str, str]] = {
    POIType.PREV_1M_HIGH: ("1m", "high"), POIType.PREV_1M_LOW: ("1m", "low"),
    POIType.PREV_5M_HIGH: ("5m", "high"), POIType.PREV_5M_LOW: ("5m", "low"),
    POIType.PREV_15M_HIGH: ("15m", "high"), POIType.PREV_15M_LOW: ("15m", "low"),
    POIType.PREV_1H_HIGH: ("1H", "high"), POIType.PREV_1H_LOW: ("1H", "low"),
    POIType.H4_HIGH: ("4H", "high"), POIType.H4_LOW: ("4H", "low"),
    POIType.PDH: ("1D", "high"), POIType.PDL: ("1D", "low"),
    POIType.WEEK_HIGH: ("1W", "high"), POIType.WEEK_LOW: ("1W", "low"),
    POIType.MONTH_HIGH: ("1M", "high"), POIType.MONTH_LOW: ("1M", "low"),
}


def _source_timestamp(candle) -> float:
    if isinstance(candle, dict):
        return float(candle.get("open_time", candle.get("bucket_start_ms", 0)))
    return float(getattr(candle, "open_time", 0))


def _is_swing_high(candles: List, index: int) -> bool:
    if index - FRACTAL_LOOKBACK < 0 or index + FRACTAL_LOOKBACK >= len(candles):
        return False
    high = cf(candles[index], "high")
    return all(cf(candles[index - n], "high") <= high and cf(candles[index + n], "high") <= high for n in range(1, FRACTAL_LOOKBACK + 1))


def _is_swing_low(candles: List, index: int) -> bool:
    if index - FRACTAL_LOOKBACK < 0 or index + FRACTAL_LOOKBACK >= len(candles):
        return False
    low = cf(candles[index], "low")
    return all(cf(candles[index - n], "low") >= low and cf(candles[index + n], "low") >= low for n in range(1, FRACTAL_LOOKBACK + 1))


class POILevelCalculatorWorker:
    """Computes UTC period levels and source-timeframe selected Flip lines."""

    def __init__(self, market_data_monitor: MarketDataMonitorLike, symbol: str, enabled_types: Dict[str, bool], on_poi_update: Callable[[str, List[POI]], None], *, display_enabled: Optional[Dict[str, bool]] = None, strategy_enabled: Optional[Dict[str, bool]] = None, zone_source_tf_enabled: Optional[Dict[str, bool]] = None) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.display_enabled = display_enabled or dict(DEFAULT_DISPLAY_ENABLED)
        self.strategy_enabled = strategy_enabled or enabled_types
        self._legacy_zone_source_mode = zone_source_tf_enabled is None
        self.zone_source_tf_enabled = zone_source_tf_enabled or {}
        self.on_poi_update = on_poi_update
        self.availability: HTFAvailability = probe_htf_availability(market_data_monitor, symbol)
        self._pois: Dict[str, POI] = {}

    def refresh_availability(self) -> None:
        self.availability = probe_htf_availability(self.mdm, self.symbol)

    def is_type_ready(self, poi_type: str) -> bool:
        if not self.strategy_enabled.get(poi_type, False):
            return False
        source_tf = POI_SOURCE_TF.get(poi_type)
        return source_tf is None or self.availability.is_available(source_tf)

    def _selected_flip_tfs(self) -> List[str]:
        if self._legacy_zone_source_mode:
            return [LEGACY_FLIP_TF]
        return [tf for tf in ZONE_SOURCE_TFS if self.zone_source_tf_enabled.get(tf, False)]

    def _line_poi(self, poi_type: str, price: float, source_tf: str, index: int, source_ts: float) -> POI:
        is_high = poi_type.endswith("_HIGH") or poi_type == POIType.PDH
        return POI(
            poi_id=f"{self.symbol}:{poi_type}", symbol=self.symbol, poi_type=poi_type,
            role="resistance" if is_high else "support", source_tf=source_tf, price=price,
            formed_at_index=index, formed_at_ts=source_ts,
            display_enabled=self.display_enabled.get(poi_type, False),
            strategy_enabled=self.strategy_enabled.get(poi_type, False),
            metadata={"source_kind": "previous_completed_futures_candle", "broker_boundary": "UTC", "source_tf": source_tf},
        )

    def _compute_prev_period_high_low(self, tf: str):
        candles = self.mdm.get_historical_candles(self.symbol, tf, LOOKBACK_DAYS_FOR_TF[tf])
        if not candles or len(candles) < 2:
            return None
        previous = candles[-2]
        return cf(previous, "high"), cf(previous, "low"), len(candles) - 2, _source_timestamp(previous)

    def _compute_line_types(self) -> List[POI]:
        results: List[POI] = []
        for poi_type, (tf, side) in LINE_MAPPING.items():
            if not self.is_type_ready(poi_type):
                continue
            previous = self._compute_prev_period_high_low(tf)
            if previous is None:
                continue
            high, low, index, source_ts = previous
            results.append(self._line_poi(poi_type, high if side == "high" else low, tf, index, source_ts))
        return results

    def _compute_flip_types(self) -> List[POI]:
        results: List[POI] = []
        support_on = self.strategy_enabled.get(POIType.SUPPORT_FLIP, False)
        resistance_on = self.strategy_enabled.get(POIType.RESISTANCE_FLIP, False)
        if not (support_on or resistance_on):
            return results
        for tf in self._selected_flip_tfs():
            candles = self.mdm.get_historical_candles(self.symbol, tf, LOOKBACK_DAYS_FOR_TF[tf])
            if not candles or len(candles) < 2 * FRACTAL_LOOKBACK + 3:
                continue
            last_close = cf(candles[-1], "close")
            if support_on:
                for index in range(len(candles) - 2, FRACTAL_LOOKBACK, -1):
                    if _is_swing_high(candles, index) and last_close > cf(candles[index], "high"):
                        source = candles[index]
                        results.append(POI(
                            poi_id=f"{self.symbol}:SUPPORT_FLIP:{tf}:{index}", symbol=self.symbol,
                            poi_type=POIType.SUPPORT_FLIP, role="support", source_tf=tf, price=cf(source, "high"),
                            formed_at_index=index, formed_at_ts=_source_timestamp(source),
                            display_enabled=self.display_enabled.get(POIType.SUPPORT_FLIP, tf in ("1m", "15m")),
                            strategy_enabled=True,
                            metadata={"source_kind": "broken_swing_high", "source_tf": tf, "broker_boundary": "UTC"},
                        ))
                        break
            if resistance_on:
                for index in range(len(candles) - 2, FRACTAL_LOOKBACK, -1):
                    if _is_swing_low(candles, index) and last_close < cf(candles[index], "low"):
                        source = candles[index]
                        results.append(POI(
                            poi_id=f"{self.symbol}:RESISTANCE_FLIP:{tf}:{index}", symbol=self.symbol,
                            poi_type=POIType.RESISTANCE_FLIP, role="resistance", source_tf=tf, price=cf(source, "low"),
                            formed_at_index=index, formed_at_ts=_source_timestamp(source),
                            display_enabled=self.display_enabled.get(POIType.RESISTANCE_FLIP, tf in ("1m", "15m")),
                            strategy_enabled=True,
                            metadata={"source_kind": "broken_swing_low", "source_tf": tf, "broker_boundary": "UTC"},
                        ))
                        break
        return results

    def recompute(self) -> List[POI]:
        pois = self._compute_line_types() + self._compute_flip_types()
        self._pois = {poi.poi_id: poi for poi in pois}
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_type_enabled(self, poi_type: str, enabled: bool) -> None:
        self.enabled_types[poi_type] = bool(enabled)
        self.strategy_enabled[poi_type] = bool(enabled)
        self.recompute()

    def set_display_enabled(self, poi_type: str, enabled: bool) -> None:
        self.display_enabled[poi_type] = bool(enabled)
        self.recompute()

    def set_source_tf_enabled(self, timeframe: str, enabled: bool) -> None:
        if timeframe not in ZONE_SOURCE_TFS:
            raise ValueError(f"Unsupported zone source timeframe: {timeframe}")
        if self._legacy_zone_source_mode:
            self._legacy_zone_source_mode = False
            self.zone_source_tf_enabled = {tf: tf == LEGACY_FLIP_TF for tf in ZONE_SOURCE_TFS}
        self.zone_source_tf_enabled[timeframe] = bool(enabled)
        self.recompute()

    async def run_forever(self, poll_seconds: float = 30.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("poi_level_calculator_worker_failed symbol=%s", self.symbol)
            await asyncio.sleep(poll_seconds)
