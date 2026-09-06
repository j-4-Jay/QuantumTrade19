"""File 04 - Setup Detection Monitor - Worker 6/7: FVG Confirmation Detector.

PATH: engines/workers/setup/fvg_confirmation_detector_worker.py (NEW FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md / 123Bear_Setup_Master_Prompt.md
Section 7: "If Candle 3 creates a Fair Value Gap with Candle 1, this is an even
stronger bonus." Confidence-score input only - NEVER rejects a setup.

Evaluates ONLY the 3 candles holding the C1/C2/C3 roles for THIS confirmed
setup - a narrower, separate check from File 03's locked FVGDetectorWorker
(which scans arbitrary HTF history for POI zones); nothing here re-derives it.

    Bull: FVG exists if C1.high < C3.low ; gap = (C1.high, C3.low)
    Bear: FVG exists if C1.low  > C3.high; gap = (C3.high, C1.low)
"""
from __future__ import annotations

from typing import Optional, Tuple

from engines.workers.setup.setup_types import SetupDirection


class FVGConfirmationDetectorWorker:
    @staticmethod
    def check(c1, c3, direction: str) -> Tuple[bool, Optional[Tuple[float, float]]]:
        if direction == SetupDirection.BULL:
            if c1.high < c3.low:
                return True, (c1.high, c3.low)
            return False, None
        if direction == SetupDirection.BEAR:
            if c1.low > c3.high:
                return True, (c3.high, c1.low)
            return False, None
        return False, None
