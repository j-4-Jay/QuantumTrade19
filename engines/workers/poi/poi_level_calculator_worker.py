"""
engines/workers/poi/poi_level_calculator_worker.py

Tier 1 Worker #1 of File 03.

Computes, per symbol and per ENABLED POI type: 1-Month H/L, 1-Week H/L,
PDH/PDL, 4H H/L, Resistance Flip, Support Flip.

Reads ONLY Market_Data_Monitor's HTF candle series (1H/4H/1D/1W/1M) via
get_live_candle()/get_historical_candles() -- never the 1m/5m/15m trading
timeframes. Never hardcodes symbols.

FIX: _compute_prev_period_high_low() previously requested a flat 5-day
lookback for every timeframe. That's fine for 1D/4H, but structurally
cannot return 2 completed candles for 1W (5 days < 1 week) or 1M (5 days
<< 1 month) -- now uses a per-timeframe lookback window.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

from .candle_access import cf
from .htf_availability import HTFAvailability, MarketDataMonitorLike, probe_htf_availability
from .poi_types import POI, POIType, POI_SOURCE_TF

logger = logging.getLogger("poi_monitor.poi_level_calculator_worker")

LINE_TYPES = [
    POIType.MONTH_HIGH, POIType.MONTH_LOW,
    POIType.WEEK_HIGH, POIType.WEEK_LOW,
    POIType.PDH, POIType.PDL,
    POIType.H4_HIGH, POIType.H4_LOW,
]
FLIP_TYPES = [POIType.RESISTANCE_FLIP, POIType.SUPPORT_FLIP]

FRACTAL_LOOKBACK = 2  # candles either side for a swing high/low fractal

# Per-timeframe lookback window for "give me the last completed period."
# Needs at least 2 completed periods worth of days, with margin.
LOOKBACK_DAYS_FOR_TF: Dict[str, int] = {
    "1H": 3,
    "4H": 5,
    "1D": 5,
    "1W": 21,   # 3 weeks, so a fresh symbol still has 2+ completed weekly candles
    "1M": 95,   # ~3 months, same margin for monthly
}


def _is_swing_high(candles: List, i: int, look: int = FRACTAL_LOOKBACK) -> bool:
    if i - look < 0 or i + look >= len(candles):
        return False
    h = cf(candles[i], "high")
    return all(cf(candles[i - k], "high") <= h for k in range(1, look + 1)) and \
        all(cf(candles[i + k], "high") <= h for k in range(1, look + 1))


def _is_swing_low(candles: List, i: int, look: int = FRACTAL_LOOKBACK) -> bool:
    if i - look < 0 or i + look >= len(candles):
        return False
    lo = cf(candles[i], "low")
    return all(cf(candles[i - k], "low") >= lo for k in range(1, look + 1)) and \
        all(cf(candles[i + k], "low") >= lo for k in range(1, look + 1))


class POILevelCalculatorWorker:
    def __init__(
        self,
        market_data_monitor: MarketDataMonitorLike,
        symbol: str,
        enabled_types: Dict[str, bool],
        on_poi_update: Callable[[str, List[POI]], None],
    ) -> None:
        self.mdm = market_data_monitor
        self.symbol = symbol
        self.enabled_types = enabled_types
        self.on_poi_update = on_poi_update
        self.availability: HTFAvailability = probe_htf_availability(market_data_monitor, symbol)
        self._last_recompute_ts: float = 0.0
        self._pois: Dict[str, POI] = {}

    def refresh_availability(self) -> None:
        self.availability = probe_htf_availability(self.mdm, self.symbol)

    def is_type_ready(self, poi_type: str) -> bool:
        if not self.enabled_types.get(poi_type, False):
            return False
        src_tf = POI_SOURCE_TF.get(poi_type)
        if src_tf is None:
            return True
        return self.availability.is_available(src_tf)

    def _line_poi(self, poi_type: str, price: float, source_tf: str, idx: int) -> POI:
        role = "resistance" if poi_type in (
            POIType.MONTH_HIGH, POIType.WEEK_HIGH, POIType.PDH, POIType.H4_HIGH,
        ) else "support"
        return POI(
            poi_id=f"{self.symbol}:{poi_type}",
            symbol=self.symbol,
            poi_type=poi_type,
            role=role,
            source_tf=source_tf,
            price=price,
            formed_at_index=idx,
            formed_at_ts=time.time(),
            active=True,
        )

    def _compute_prev_period_high_low(self, tf: str) -> Optional[tuple[float, float, int]]:
        """Returns (high, low, index) of the most recently *completed* candle
        on the given TF. CoinDCX's history returns the still-forming
        current-period candle as the last row -- index -2 is the last
        genuinely completed one, -1 must be skipped."""
        lookback_days = LOOKBACK_DAYS_FOR_TF.get(tf, 5)
        candles = self.mdm.get_historical_candles(self.symbol, tf, lookback_days)
        if not candles or len(candles) < 2:
            return None
        prev = candles[-2]
        return cf(prev, "high"), cf(prev, "low"), len(candles) - 2

    def _compute_line_types(self) -> List[POI]:
        results: List[POI] = []
        mapping = {
            POIType.MONTH_HIGH: ("1M", "high"), POIType.MONTH_LOW: ("1M", "low"),
            POIType.WEEK_HIGH: ("1W", "high"), POIType.WEEK_LOW: ("1W", "low"),
            POIType.PDH: ("1D", "high"), POIType.PDL: ("1D", "low"),
            POIType.H4_HIGH: ("4H", "high"), POIType.H4_LOW: ("4H", "low"),
        }
        for poi_type, (tf, side) in mapping.items():
            if not self.is_type_ready(poi_type):
                continue
            hl = self._compute_prev_period_high_low(tf)
            if hl is None:
                continue
            high, low, idx = hl
            price = high if side == "high" else low
            results.append(self._line_poi(poi_type, price, tf, idx))
        return results

    def _compute_flip_types(self) -> List[POI]:
        """Resistance Flip / Support Flip: a swing high/low on the 4H series
        that price has since closed through and is expected to act as the
        opposite role on retest (per 123Bull/Bear Section 5 "flipped zone")."""
        results: List[POI] = []
        if not self.availability.is_available("4H"):
            return results
        candles = self.mdm.get_historical_candles(self.symbol, "4H", 30)
        if not candles or len(candles) < 2 * FRACTAL_LOOKBACK + 3:
            return results
        last_close = cf(candles[-1], "close")

        if self.enabled_types.get(POIType.SUPPORT_FLIP, False):
            for i in range(len(candles) - 2, FRACTAL_LOOKBACK, -1):
                if _is_swing_high(candles, i):
                    level = cf(candles[i], "high")
                    if last_close > level:  # broken upward -> old resistance flips to support
                        results.append(POI(
                            poi_id=f"{self.symbol}:SUPPORT_FLIP:{i}",
                            symbol=self.symbol, poi_type=POIType.SUPPORT_FLIP,
                            role="support", source_tf="4H", price=level,
                            formed_at_index=i, formed_at_ts=time.time(),
                        ))
                        break

        if self.enabled_types.get(POIType.RESISTANCE_FLIP, False):
            for i in range(len(candles) - 2, FRACTAL_LOOKBACK, -1):
                if _is_swing_low(candles, i):
                    level = cf(candles[i], "low")
                    if last_close < level:  # broken downward -> old support flips to resistance
                        results.append(POI(
                            poi_id=f"{self.symbol}:RESISTANCE_FLIP:{i}",
                            symbol=self.symbol, poi_type=POIType.RESISTANCE_FLIP,
                            role="resistance", source_tf="4H", price=level,
                            formed_at_index=i, formed_at_ts=time.time(),
                        ))
                        break
        return results

    def recompute(self) -> List[POI]:
        pois = self._compute_line_types() + self._compute_flip_types()
        self._pois = {p.poi_id: p for p in pois}
        self._last_recompute_ts = time.time()
        self.on_poi_update(self.symbol, list(self._pois.values()))
        return list(self._pois.values())

    def set_type_enabled(self, poi_type: str, enabled: bool) -> None:
        """Live toggle -- Settings calls straight into this. Immediately
        recomputes so the Dashboard reflects the change with no restart."""
        self.enabled_types[poi_type] = enabled
        if not enabled:
            self._pois = {k: v for k, v in self._pois.items() if v.poi_type != poi_type}
        self.recompute()

    async def run_forever(self, poll_seconds: float = 30.0) -> None:
        import asyncio
        while True:
            try:
                self.recompute()
            except Exception:  # noqa: BLE001
                logger.exception("POI_Level_Calculator_Worker failed for %s", self.symbol)
            await asyncio.sleep(poll_seconds)
