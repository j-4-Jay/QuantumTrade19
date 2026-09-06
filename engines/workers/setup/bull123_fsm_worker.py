"""File 04 - Setup Detection Monitor - Worker 3/7: Bull123 FSM.

PATH: engines/workers/setup/bull123_fsm_worker.py (NEW FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md Section 1 (Red, Green, Green)
and Section 6. Shared, tested mechanics live in _fsm_base.py - see its
IMPLEMENTATION NOTE before modifying anything. This file only fixes Bull's
direction/colors and Section 6.5's confirmation rule:

    "Candle 3 ... must close ABOVE Candle 2's HIGHEST price."

Runs independently per timeframe (1m/5m/15m never share state).
"""
from __future__ import annotations

from engines.workers.setup._fsm_base import _Base123FSMWorker
from engines.workers.setup.setup_types import CandleColor, SetupDirection


class Bull123FSMWorker(_Base123FSMWorker):
    direction = SetupDirection.BULL
    c1_color = CandleColor.RED
    c2_color = CandleColor.GREEN

    def _confirms_extreme(self, c3, c2) -> bool:
        return c3.close > c2.high
