from __future__ import annotations
from typing import Callable
from engines.event_bus.bus import event_bus

class LogoutWorker:
    def __init__(self):
        self.open_trades_checker: Callable[[], bool] = lambda: False
    def has_open_trades(self):
        return self.open_trades_checker()
    def request_close_all_trades(self):
        event_bus.publish("trade.close_all_requested", {})
    def request_keep_trades_running(self):
        event_bus.publish("trade.keep_running_requested", {})
