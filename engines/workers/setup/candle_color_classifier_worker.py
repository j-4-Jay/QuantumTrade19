"""File 04 - Setup Detection Monitor - Worker 1/7: Candle Color Classifier.

PATH: engines/workers/setup/candle_color_classifier_worker.py (NEW FILE)

Source of truth: 123Bull_Setup_Master_Prompt.md Section 3 / 123Bear_Setup_Master_Prompt.md
Section 3 (identical wording in both):

    Green candle = close > open.
    Red candle   = close < open.
    Only the final close-vs-open color counts - wick/shape/size is irrelevant.

A close == open candle is a doji and has NO rule-defined color. classify()
returns None for this case; every downstream File 04 worker must treat None
as "this candle can never hold a role," never crash on it.
"""
from __future__ import annotations

from typing import Optional

from engines.workers.setup.setup_types import CandleColor


class CandleColorClassifierWorker:
    @staticmethod
    def classify(candle) -> Optional[str]:
        if candle.close > candle.open:
            return CandleColor.GREEN
        if candle.close < candle.open:
            return CandleColor.RED
        return None

    @staticmethod
    def is_green(candle) -> bool:
        return CandleColorClassifierWorker.classify(candle) == CandleColor.GREEN

    @staticmethod
    def is_red(candle) -> bool:
        return CandleColorClassifierWorker.classify(candle) == CandleColor.RED
