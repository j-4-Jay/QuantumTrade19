"""File 04 - Setup Detection Monitor - Worker 4/7: Bear123 FSM.
PATH: engines/workers/setup/bear123_fsm_worker.py (REPLACE ENTIRE FILE)

Source of truth: 123Bear_Setup_Master_Prompt.md Sections 1 & 6. Shared
mechanics live in _fsm_base.py - read its header before editing. This file
only supplies Bear's confirmation rule (Section 6 step 5 + Section 1's
Green/Red/Red pattern): Candle2 AND Candle3 must both be RED, and Candle3
must close below Candle2's low.

Runs independently per timeframe, and never shares a candle with
Bull123FSMWorker - both workers for the same (symbol, timeframe) MUST be
constructed with the same shared CandleLockRegistry instance.
"""
from __future__ import annotations

from engines.workers.setup._fsm_base import _Base123FSMWorker
from engines.workers.setup.setup_types import CandleColor, SetupDirection


class Bear123FSMWorker(_Base123FSMWorker):
    direction = SetupDirection.BEAR

    def _confirms_extreme(self, c3, c2) -> bool:
        return (
            self._classifier.classify(c2) == CandleColor.RED
            and self._classifier.classify(c3) == CandleColor.RED
            and c3.close < c2.low
        )
