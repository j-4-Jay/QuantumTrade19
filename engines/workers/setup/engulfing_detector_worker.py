"""File 04 - Setup Detection Monitor - Worker 5/7: Engulfing Detector.

PATH: engines/workers/setup/engulfing_detector_worker.py (NEW FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md / 123Bear_Setup_Master_Prompt.md
Section 7: "If Candle 2 fully engulfs Candle 1, this is a strong bonus."
Confidence-score input only - NEVER rejects a setup.
"""
from __future__ import annotations


class EngulfingDetectorWorker:
    @staticmethod
    def candle2_engulfs_candle1(c1, c2) -> bool:
        c1_low = min(c1.open, c1.close)
        c1_high = max(c1.open, c1.close)
        c2_low = min(c2.open, c2.close)
        c2_high = max(c2.open, c2.close)
        return c2_low <= c1_low and c2_high >= c1_high
