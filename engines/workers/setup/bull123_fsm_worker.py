"""File 04 - Setup Detection Monitor - Worker 3/7: Bull123 FSM.
PATH: engines/workers/setup/bull123_fsm_worker.py (REPLACE ENTIRE FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md Sections 1 & 6. Shared,
validated mechanics live in _fsm_base.py - read its header before editing.
This file only supplies Bull's confirmation rule (Section 6 step 5 + Section
1's Red/Green/Green pattern): Candle2 AND Candle3 must both be GREEN, and
Candle3 must close above Candle2's high.
"""
from __future__ import annotations

from engines.workers.setup._fsm_base import _Base123FSMWorker
from engines.workers.setup.setup_types import CandleColor, SetupDirection


class Bull123FSMWorker(_Base123FSMWorker):
    direction = SetupDirection.BULL

    def _confirms_extreme(self, c3, c2) -> bool:
        return (
            self._classifier.classify(c2) == CandleColor.GREEN
            and self._classifier.classify(c3) == CandleColor.GREEN
            and c3.close > c2.high
        )
