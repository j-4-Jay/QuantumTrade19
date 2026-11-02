"""
FULL PATH: tests/workers/market_data/test_candle_reconcile_settle.py
Settle fetches (1.5 s, 4 s, 8 s after a candle close) for CandleReconcileWorker.
"""
from engines.workers.market_data.candle_reconcile_worker import CandleReconcileWorker

BOUNDARY_S = 1_700_000_040.0


def _worker(calls):
    def fetch(symbol, tf, start_ms, end_ms):
        calls.append((tf, end_ms))
        return [object()]

    return CandleReconcileWorker(
        fetch_range=fetch, apply=lambda s, t, c, n: [], get_symbols=lambda: ["B-XAU_USDT"],
        intervals={"1m": 10_000.0},
    )


def test_settle_fetch_runs_once_per_offset():
    calls = []
    w = _worker(calls)
    w._due[("B-XAU_USDT", "1m")] = 10 ** 12
    assert w.run_once(BOUNDARY_S + 1.0) == 0
    assert w.run_once(BOUNDARY_S + 1.6) == 1
    assert w.run_once(BOUNDARY_S + 1.7) == 0
    assert w.run_once(BOUNDARY_S + 4.1) == 1
    assert w.run_once(BOUNDARY_S + 4.2) == 0
    assert w.run_once(BOUNDARY_S + 8.3) == 1
    assert w.run_once(BOUNDARY_S + 8.4) == 0
    assert len(calls) == 3


def test_settle_fetch_repeats_next_minute():
    calls = []
    w = _worker(calls)
    w._due[("B-XAU_USDT", "1m")] = 10 ** 12
    assert w.run_once(BOUNDARY_S + 1.6) == 1
    assert w.run_once(BOUNDARY_S + 60.0 + 1.6) == 1
    assert len(calls) == 2


def test_late_settle_is_skipped_after_five_seconds():
    calls = []
    w = _worker(calls)
    w._due[("B-XAU_USDT", "1m")] = 10 ** 12
    assert w.run_once(BOUNDARY_S + 14.0) == 0
