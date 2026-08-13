from engines.workers.security.logout_worker import LogoutWorker
from engines.event_bus.bus import event_bus

def test_defaults_no_open_trades():
    w = LogoutWorker(); assert w.has_open_trades() is False

def test_custom_checker():
    w = LogoutWorker(); w.open_trades_checker = lambda: True
    assert w.has_open_trades() is True

def test_close_trades_event():
    w = LogoutWorker(); received = []
    event_bus.subscribe("trade.close_all_requested", lambda d: received.append(d))
    w.request_close_all_trades()
    assert len(received) == 1
