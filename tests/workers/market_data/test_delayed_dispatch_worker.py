"""
FULL PATH: tests/workers/market_data/test_delayed_dispatch_worker.py
FT-H.33: a closed candle reaches the setup monitor only after the settle delay.
"""
import threading

from engines.workers.market_data.candle_builder_worker import Candle
from engines.workers.market_data.delayed_dispatch_worker import (
    DelayedDispatchWorker, SETUP_SETTLE_DELAY_S, SETTLE_TIMEFRAMES,
)


def _candle(open_time=0, close=100.0, tf="1m"):
    return Candle(
        symbol="B-XAU_USDT", timeframe=tf, open_time=open_time, close_time=open_time + 59_999,
        open=100.0, high=101.0, low=99.0, close=close, volume=10.0, is_closed=True,
    )


def test_not_delivered_before_delay_and_delivered_after():
    got = []
    w = DelayedDispatchWorker(got.append)
    c = _candle()
    w.submit(c, 9.0, now=100.0)
    assert w.run_due(108.9) == 0
    assert got == []
    assert w.run_due(109.0) == 1
    assert got == [c]
    assert w.pending() == 0


def test_delivery_order_follows_due_time_then_submit_order():
    got = []
    w = DelayedDispatchWorker(got.append)
    a, b, c = _candle(1), _candle(2), _candle(3)
    w.submit(a, 9.0, now=100.0)
    w.submit(b, 9.0, now=100.0)
    w.submit(c, 5.0, now=100.0)
    assert w.run_due(120.0) == 3
    assert got == [c, a, b]


def test_candle_corrected_during_the_wait_is_delivered_corrected():
    got = []
    w = DelayedDispatchWorker(got.append)
    c = _candle(close=100.0)
    w.submit(c, 9.0, now=100.0)
    c.close = 100.5
    w.run_due(110.0)
    assert got[0].close == 100.5


def test_failing_callback_does_not_stop_later_items():
    got = []

    def deliver(item):
        if item.open_time == 1:
            raise RuntimeError("boom")
        got.append(item)

    w = DelayedDispatchWorker(deliver)
    w.submit(_candle(1), 1.0, now=0.0)
    w.submit(_candle(2), 1.0, now=0.0)
    assert w.run_due(5.0) == 2
    assert [c.open_time for c in got] == [2]


def test_background_thread_delivers():
    done = threading.Event()
    got = []

    def deliver(item):
        got.append(item)
        done.set()

    w = DelayedDispatchWorker(deliver)
    w.start()
    try:
        w.submit(_candle(), 0.05)
        assert done.wait(3.0)
        assert len(got) == 1
    finally:
        w.stop()


def test_settings():
    assert SETUP_SETTLE_DELAY_S == 9.0
    assert SETTLE_TIMEFRAMES == {"1m", "5m", "15m"}


def _bare_monitor(reconcile):
    from engines.monitors.market_data_monitor import MarketDataMonitor
    m = object.__new__(MarketDataMonitor)
    m._lock = threading.RLock()
    m._reconcile_worker = reconcile
    m._candle_close_subscribers = []
    return m


def test_monitor_defers_only_reconciled_timeframes(monkeypatch):
    monkeypatch.delenv("QT19_DISABLE_RECONCILE", raising=False)
    m = _bare_monitor(object())
    try:
        assert m._defer_close_notification(_candle(tf="1m")) is True
        assert m._defer_close_notification(_candle(tf="1H")) is False
    finally:
        d = m.__dict__.get("_close_dispatcher")
        if d is not None:
            d.stop()


def test_monitor_does_not_defer_when_reconcile_is_off(monkeypatch):
    monkeypatch.delenv("QT19_DISABLE_RECONCILE", raising=False)
    m = _bare_monitor(None)
    assert m._defer_close_notification(_candle(tf="1m")) is False
