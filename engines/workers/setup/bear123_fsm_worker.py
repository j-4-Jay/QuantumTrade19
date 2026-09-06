"""File 04 - Setup Detection Monitor - Worker 4/7: Bear123 FSM.

PATH: engines/workers/setup/bear123_fsm_worker.py (NEW FILE)

Source of truth: 123Bear_Setup_Master_Prompt.md Section 1 (Green, Red, Red)
and Section 6. Shared mechanics live in _fsm_base.py - see its IMPLEMENTATION
NOTE. This file only fixes Bear's direction/colors and Section 6.5's
confirmation rule:

    "Candle 3 ... must close BELOW Candle 2's LOWEST price."

Runs independently per timeframe, and never shares a candle with
Bull123FSMWorker - both workers for the same (symbol, timeframe) MUST be
constructed with the same shared CandleLockRegistry instance.
"""
from __future__ import annotations

from engines.workers.setup._fsm_base import _Base123FSMWorker
from engines.workers.setup.setup_types import CandleColor, SetupDirection


class Bear123FSMWorker(_Base123FSMWorker):
    direction = SetupDirection.BEAR
    c1_color = CandleColor.GREEN
    c2_color = CandleColor.RED

    def _confirms_extreme(self, c3, c2) -> bool:
        return c3.close < c2.low
