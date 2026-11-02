"""
FULL PATH: tests/workers/market_data/test_candle_reconcile_worker.py
Tests for CandleReconcileWorker (no network).
"""
from engines.workers.market_data.candle_reconcile_worker import CandleReconcileWorker


def _make(fetch, apply=None, symbols=("B-XAU_USDT",)):
    applied = []

    def default_apply(symbol, tf, candles, now_ms):
        applied.append((symbol, tf, len(candles), now_ms))
        return []

    worker = CandleReconcileWorker(
        fetch_range=fetch, apply=apply or default_apply, get_symbols=lambda: list(symbols),
    )
    return worker, applied


def test_one_fetch_per_run_and_all_timeframes_covered():
    calls = []

    def fetch(symbol, tf, start_ms, end_ms):
        calls.append((symbol, tf))
        return [object()]

    worker, applied = _make(fetch)
    assert worker.run_once(1000.0) == 1
    assert worker.run_once(1000.0) == 1
    assert worker.run_once(1000.0) == 1
    assert worker.run_once(1000.0) == 0
    assert sorted(tf for _, tf in calls) == ["15m", "1m", "5m"]
    assert len(applied) == 3


def test_intervals_respected():
    calls = []

    def fetch(symbol, tf, start_ms, end_ms):
        calls.append(tf)
        return [object()]

    worker, _ = _make(fetch)
    for _ in range(3):
        worker.run_once(1000.0)
    calls.clear()
    assert worker.run_once(1005.0) == 0
    assert worker.run_once(1011.0) == 1
    assert calls == ["1m"]


def test_failure_backs_off_and_recovers():
    state = {"fail": True, "n": 0}

    def fetch(symbol, tf, start_ms, end_ms):
        state["n"] += 1
        if state["fail"]:
            raise TimeoutError("read timeout")
        return [object()]

    worker, _ = _make(fetch)
    worker._intervals = {"1m": 10.0}
    assert worker.run_once(1000.0) == 1
    assert worker.run_once(1010.0) == 0
    assert worker.run_once(1021.0) == 1
    assert state["n"] == 2
    state["fail"] = False
    assert worker.run_once(1100.0) == 1
    assert worker.run_once(1105.0) == 0
    assert worker.run_once(1111.0) == 1


def test_window_start_is_aligned_to_candle_boundary():
    seen = []

    def fetch(symbol, tf, start_ms, end_ms):
        seen.append((tf, start_ms, end_ms))
        return [object()]

    worker, _ = _make(fetch)
    worker._intervals = {"15m": 30.0}
    worker.run_once(1_700_000_123.0)
    tf, start_ms, end_ms = seen[0]
    assert tf == "15m"
    assert start_ms % 900_000 == 0
    assert end_ms == 1_700_000_123_000
