"""
FULL PATH: tests/monitors/test_callout_skip_logging.py
A setup that cannot get a callout must leave a log line (never a silent skip).
"""
import logging
from types import SimpleNamespace

from engines.workers.setup.setup_callout_helper import build_setup_callouts


def test_setup_without_candle_is_skipped_and_logged(caplog):
    broken = SimpleNamespace(event_id="E1", c1=None, c2=None, c3=None, direction="BULL", timeframe="5m")
    with caplog.at_level(logging.WARNING, logger="setup.callout_helper"):
        result = build_setup_callouts([broken], 0.01, 7)
    assert result == []
    assert any("callout_skipped_missing_candle" in r.getMessage() and "E1" in r.getMessage() for r in caplog.records)
