"""File 04 shared types: candle color, POI interaction, candle roles, pending/confirmed setups.

PATH: engines/workers/setup/setup_types.py (NEW FILE)

Single source of truth for ALL setup rules: 123Bull_Setup_Master_Prompt.md and
123Bear_Setup_Master_Prompt.md. This module only defines shared data shapes used
by every Tier 1 Worker in File 04 - it contains zero setup/FSM logic itself.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any, Dict, List, Optional


class CandleColor(str, Enum):
    GREEN = "Green"
    RED = "Red"


class InteractionType(str, Enum):
    TOUCH = "Touch"
    SWEEP = "Sweep"
    CROSS = "Cross"


class SetupDirection(str, Enum):
    BULL = "123Bull"
    BEAR = "123Bear"


class CandleRole(str, Enum):
    C1 = "Candle1"
    C2 = "Candle2"
    C3 = "Candle3"


@dataclass
class CandleRef:
    """Identifies exactly one closed candle - the unit that gets locked once used
    in a CONFIRMED setup. (symbol, timeframe, open_time) is unique per candle."""

    symbol: str
    timeframe: str
    open_time: int

    def key(self) -> tuple:
        return (self.symbol, self.timeframe, self.open_time)


@dataclass
class Interaction:
    """One closed candle's geometric relationship to one POI (Section 4)."""

    poi_id: str
    interaction_type: str  # InteractionType
    is_retest: bool = False
    retest_flipped: bool = False  # True == "double-cross flip" case (Scenario B, opposite direction)
    search_direction: str = ""  # SetupDirection this interaction is eligible to feed


@dataclass
class PendingSetup:
    """One in-flight Candle1/Candle2 (or Candle1-only) attempt for one POI, one
    timeframe, one direction (Bull or Bear)."""

    pending_id: str
    symbol: str
    timeframe: str
    poi_id: str
    direction: str  # SetupDirection
    stage: str  # "SEARCHING_C2" | "WAITING_C3"
    c1: Optional[Any] = None  # Candle
    c2: Optional[Any] = None  # Candle
    updated_at: float = field(default_factory=time)


@dataclass
class ConfirmedSetup:
    """One CONFIRMED 3-candle setup. Emitted exactly once, with a unique event_id,
    onto the internal event bus for Confidence Monitor / Execution Monitor."""

    event_id: str
    symbol: str
    timeframe: str
    poi_id: str
    direction: str  # SetupDirection
    c1: Any
    c2: Any
    c3: Any
    confirmed_at: float
    engulfing: bool = False
    fvg_confirmation: bool = False
    fvg_range: Optional[tuple] = None
    sl_price: Optional[float] = None
    is_mtf_cascade_result: bool = False
    cascade_parent_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new_event_id() -> str:
        return str(uuid.uuid4())
