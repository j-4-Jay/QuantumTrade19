"""File 04 shared support: global candle-lock registry.

PATH: engines/workers/setup/candle_lock_registry.py (NEW FILE)

Enforces the locked no-reuse rule from 123Bull_Setup_Master_Prompt.md Section 6.7
and 123Bear_Setup_Master_Prompt.md Section 6.7: once a candle is part of a
CONFIRMED setup, it can never be reused as Candle1/2/3 in any other setup search -
Bull or Bear, same POI or a different one, same timeframe only.

One single instance of this registry must be shared across Bull123_FSM_Worker and
Bear123_FSM_Worker for the SAME (symbol, timeframe).
"""
from __future__ import annotations

from typing import Set, Tuple

CandleKey = Tuple[str, str, int]  # (symbol, timeframe, open_time)


class CandleLockRegistry:
    def __init__(self) -> None:
        self._locked: Set[CandleKey] = set()

    @staticmethod
    def _key(symbol: str, timeframe: str, open_time: int) -> CandleKey:
        return (symbol, timeframe, open_time)

    def is_locked(self, symbol: str, timeframe: str, open_time: int) -> bool:
        return self._key(symbol, timeframe, open_time) in self._locked

    def any_locked(self, candles) -> bool:
        return any(self.is_locked(c.symbol, c.timeframe, c.open_time) for c in candles)

    def lock_all(self, candles) -> None:
        for c in candles:
            self._locked.add(self._key(c.symbol, c.timeframe, c.open_time))

    def locked_count(self) -> int:
        return len(self._locked)
