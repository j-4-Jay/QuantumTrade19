"""
engines/workers/poi/poi_types.py
Shared data structures for the POI Monitor (File 03). No business logic here —
every Worker and the Tier-2 assembly import from this single module so the
shapes never drift between files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any, Dict, Optional


class POIType(str, Enum):
    """Every POI type the app can compute. Matches Settings toggle labels exactly."""
    MONTH_HIGH = "1M_HIGH"
    MONTH_LOW = "1M_LOW"
    WEEK_HIGH = "1W_HIGH"
    WEEK_LOW = "1W_LOW"
    PDH = "PDH"
    PDL = "PDL"
    H4_HIGH = "4H_HIGH"
    H4_LOW = "4H_LOW"
    RESISTANCE_FLIP = "RESISTANCE_FLIP"
    SUPPORT_FLIP = "SUPPORT_FLIP"
    FVG = "FVG"
    ORDER_BLOCK = "ORDER_BLOCK"
    INVERSE_FVG = "INVERSE_FVG"


# Default ON/OFF per project instructions: PDH/PDL and 4H H/L default ON, rest OFF.
DEFAULT_ENABLED: Dict[str, bool] = {
    POIType.MONTH_HIGH: False,
    POIType.MONTH_LOW: False,
    POIType.WEEK_HIGH: False,
    POIType.WEEK_LOW: False,
    POIType.PDH: True,
    POIType.PDL: True,
    POIType.H4_HIGH: True,
    POIType.H4_LOW: True,
    POIType.RESISTANCE_FLIP: False,
    POIType.SUPPORT_FLIP: False,
    POIType.FVG: False,
    POIType.ORDER_BLOCK: False,
    POIType.INVERSE_FVG: False,
}

# Which source HTF timeframe each line-POI type is derived from.
POI_SOURCE_TF: Dict[str, str] = {
    POIType.MONTH_HIGH: "1M",
    POIType.MONTH_LOW: "1M",
    POIType.WEEK_HIGH: "1W",
    POIType.WEEK_LOW: "1W",
    POIType.PDH: "1D",
    POIType.PDL: "1D",
    POIType.H4_HIGH: "4H",
    POIType.H4_LOW: "4H",
    POIType.RESISTANCE_FLIP: "4H",
    POIType.SUPPORT_FLIP: "4H",
}

# The full candidate HTF series the Market Data Monitor is expected to expose.
# File 03 must not assume all of these are populated — see htf_availability.py.
POI_TFS = ["1H", "4H", "1D", "1W", "1M"]


class POIState(str, Enum):
    APPROACHING = "Approaching"
    HIT = "Hit"
    CROSSED = "Crossed"
    RETESTING = "Retesting"


@dataclass
class POI:
    """One Point of Interest, line or price-range."""
    poi_id: str
    symbol: str
    poi_type: str                       # one of POIType values
    role: str                           # "resistance" | "support"
    source_tf: str
    price: Optional[float] = None       # set for line POIs
    price_high: Optional[float] = None  # set for range POIs (FVG/OB/InverseFVG)
    price_low: Optional[float] = None
    formed_at_index: int = -1
    formed_at_ts: float = 0.0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_range(self) -> bool:
        return self.price_high is not None and self.price_low is not None

    def mid_price(self) -> float:
        if self.is_range():
            return (self.price_high + self.price_low) / 2.0
        return self.price


@dataclass
class POIStateRecord:
    """Live tracking state for one POI, independent of every other POI."""
    poi_id: str
    symbol: str
    distance_ticks: float
    state: str
    last_touch_ts: Optional[float]
    last_price: float
    crossed_direction: Optional[str] = None  # "up" | "down", set once Crossed fires
    updated_at: float = field(default_factory=time)
