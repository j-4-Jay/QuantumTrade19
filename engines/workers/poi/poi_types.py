"""Shared POI structures and File 03.1 defaults.

PATH: engines/workers/poi/poi_types.py (REPLACE ENTIRE FILE)

FIX (default Display changed per explicit request) - DEFAULT_DISPLAY_ENABLED
no longer includes WEEK_HIGH/WEEK_LOW/MONTH_HIGH/MONTH_LOW - only
H4_HIGH/H4_LOW/PDH/PDL default to Display=ON now. DEFAULT_STRATEGY_ENABLED
is UNCHANGED (it already only had these same 4 types True). Every other
POI type (including Week/Month lines, all zone types) still defaults to
both Display and Strategy = OFF.
"""
from __future__ import annotations


from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any, Dict, Optional



LINE_SOURCE_TFS = ("1m", "5m", "15m", "1H", "4H", "1D", "1W", "1M")
ZONE_SOURCE_TFS = LINE_SOURCE_TFS



class POIType(str, Enum):
    """Every POI type the POI engine can compute."""


    PREV_1M_HIGH = "P1M_HIGH"
    PREV_1M_LOW = "P1M_LOW"
    PREV_5M_HIGH = "P5M_HIGH"
    PREV_5M_LOW = "P5M_LOW"
    PREV_15M_HIGH = "P15M_HIGH"
    PREV_15M_LOW = "P15M_LOW"
    PREV_1H_HIGH = "P1H_HIGH"
    PREV_1H_LOW = "P1H_LOW"


    H4_HIGH = "4H_HIGH"
    H4_LOW = "4H_LOW"
    PDH = "PDH"
    PDL = "PDL"
    WEEK_HIGH = "1W_HIGH"
    WEEK_LOW = "1W_LOW"
    MONTH_HIGH = "1M_HIGH"
    MONTH_LOW = "1M_LOW"


    RESISTANCE_FLIP = "RESISTANCE_FLIP"
    SUPPORT_FLIP = "SUPPORT_FLIP"
    FVG = "FVG"
    ORDER_BLOCK = "ORDER_BLOCK"
    INVERSE_FVG = "INVERSE_FVG"



LINE_POI_TYPES = (
    POIType.PREV_1M_HIGH,
    POIType.PREV_1M_LOW,
    POIType.PREV_5M_HIGH,
    POIType.PREV_5M_LOW,
    POIType.PREV_15M_HIGH,
    POIType.PREV_15M_LOW,
    POIType.PREV_1H_HIGH,
    POIType.PREV_1H_LOW,
    POIType.H4_HIGH,
    POIType.H4_LOW,
    POIType.PDH,
    POIType.PDL,
    POIType.WEEK_HIGH,
    POIType.WEEK_LOW,
    POIType.MONTH_HIGH,
    POIType.MONTH_LOW,
)


ZONE_POI_TYPES = (
    POIType.RESISTANCE_FLIP,
    POIType.SUPPORT_FLIP,
    POIType.FVG,
    POIType.INVERSE_FVG,
    POIType.ORDER_BLOCK,
)



POI_SOURCE_TF: Dict[str, str] = {
    POIType.PREV_1M_HIGH: "1m",
    POIType.PREV_1M_LOW: "1m",
    POIType.PREV_5M_HIGH: "5m",
    POIType.PREV_5M_LOW: "5m",
    POIType.PREV_15M_HIGH: "15m",
    POIType.PREV_15M_LOW: "15m",
    POIType.PREV_1H_HIGH: "1H",
    POIType.PREV_1H_LOW: "1H",
    POIType.H4_HIGH: "4H",
    POIType.H4_LOW: "4H",
    POIType.PDH: "1D",
    POIType.PDL: "1D",
    POIType.WEEK_HIGH: "1W",
    POIType.WEEK_LOW: "1W",
    POIType.MONTH_HIGH: "1M",
    POIType.MONTH_LOW: "1M",
}



POI_LABELS: Dict[str, str] = {
    POIType.PREV_1M_HIGH: "P1m H",
    POIType.PREV_1M_LOW: "P1m L",
    POIType.PREV_5M_HIGH: "P5m H",
    POIType.PREV_5M_LOW: "P5m L",
    POIType.PREV_15M_HIGH: "P15m H",
    POIType.PREV_15M_LOW: "P15m L",
    POIType.PREV_1H_HIGH: "P1H H",
    POIType.PREV_1H_LOW: "P1H L",
    POIType.H4_HIGH: "P4H H",
    POIType.H4_LOW: "P4H L",
    POIType.PDH: "PDH",
    POIType.PDL: "PDL",
    POIType.WEEK_HIGH: "PWH",
    POIType.WEEK_LOW: "PWL",
    POIType.MONTH_HIGH: "PMH",
    POIType.MONTH_LOW: "PML",
    POIType.RESISTANCE_FLIP: "Resistance Flip",
    POIType.SUPPORT_FLIP: "Support Flip",
    POIType.FVG: "FVG",
    POIType.INVERSE_FVG: "iFVG",
    POIType.ORDER_BLOCK: "OB",
}



DEFAULT_DISPLAY_ENABLED: Dict[str, bool] = {
    poi_type: False for poi_type in POIType
}
DEFAULT_DISPLAY_ENABLED.update(
    {
        POIType.H4_HIGH: True,
        POIType.H4_LOW: True,
        POIType.PDH: True,
        POIType.PDL: True,
    }
)


DEFAULT_STRATEGY_ENABLED: Dict[str, bool] = {
    poi_type: False for poi_type in POIType
}
DEFAULT_STRATEGY_ENABLED.update(
    {
        POIType.H4_HIGH: True,
        POIType.H4_LOW: True,
        POIType.PDH: True,
        POIType.PDL: True,
    }
)


DEFAULT_ZONE_SOURCE_TF_ENABLED: Dict[str, bool] = {
    "1m": True,
    "5m": False,
    "15m": True,
    "1H": False,
    "4H": False,
    "1D": False,
    "1W": False,
    "1M": False,
}


# Legacy compatibility: existing File 03 workers use this map for calculation
# eligibility. In File 03.1 it maps to strategy eligibility.
DEFAULT_ENABLED: Dict[str, bool] = dict(DEFAULT_STRATEGY_ENABLED)


# Legacy compatibility: existing availability code imports POI_TFS.
POI_TFS = list(LINE_SOURCE_TFS)



class POIState(str, Enum):
    APPROACHING = "Approaching"
    HIT = "Hit"
    CROSSED = "Crossed"
    RETESTING = "Retesting"



@dataclass
class POI:
    """One system Point of Interest: line or price-range."""


    poi_id: str
    symbol: str
    poi_type: str
    role: str
    source_tf: str
    price: Optional[float] = None
    price_high: Optional[float] = None
    price_low: Optional[float] = None
    formed_at_index: int = -1
    formed_at_ts: float = 0.0
    active: bool = True
    display_enabled: bool = True
    strategy_enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


    def is_range(self) -> bool:
        return self.price_high is not None and self.price_low is not None


    def mid_price(self) -> float:
        if self.is_range():
            return (self.price_high + self.price_low) / 2.0
        if self.price is None:
            raise ValueError(f"POI {self.poi_id} has no price.")
        return self.price


    @property
    def chart_label(self) -> str:
        return POI_LABELS.get(self.poi_type, str(self.poi_type))


    @property
    def line_width_px(self) -> int:
        if self.is_range():
            return 1
        return 2 if self.role == "resistance" else 1



@dataclass
class POIStateRecord:
    """Live tracking state for one POI, independent of all others."""


    poi_id: str
    symbol: str
    distance_ticks: float
    state: str
    last_touch_ts: Optional[float]
    last_price: float
    crossed_direction: Optional[str] = None
    updated_at: float = field(default_factory=time)
