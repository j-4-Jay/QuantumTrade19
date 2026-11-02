"""
FULL PATH: engines/workers/market_data/delayed_dispatch_worker.py
File 02 - Market Data Monitor - FT-H.33 (thread 008)

Holds a closed candle for a few seconds before it is handed to the setup
monitor and the outcome worker, so the exchange can still correct it (it
settles about 7 s after the close; corrections arrive 1.5, 4 and 8 s after).
One background thread, delivery in due-time order. It never places orders and
never touches broker credentials.
"""
from __future__ import annotations

import heapq
import itertools
import logging
import threading
import time
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger("market_data.delayed_dispatch")

SETUP_SETTLE_DELAY_S = 9.0
SETTLE_TIMEFRAMES = frozenset({"1m", "5m", "15m"})


class DelayedDispatchWorker:
    def __init__(self, deliver: Callable[[Any], None], time_fn: Optional[Callable[[], float]] = None) -> None:
        self._deliver = deliver
        self._time_fn = time_fn or time.time
        self._heap: List[Tuple[float, int, Any]] = []
        self._seq = itertools.count()
        self._cond = threading.Condition()
        self._stopped = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stopped = False
        self._thread = threading.Thread(target=self._loop, name="CandleDelayedDispatch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify_all()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

    def submit(self, item: Any, delay_s: float, now: Optional[float] = None) -> None:
        due = (self._time_fn() if now is None else now) + delay_s
        with self._cond:
            heapq.heappush(self._heap, (due, next(self._seq), item))
            self._cond.notify_all()

    def pending(self) -> int:
        with self._cond:
            return len(self._heap)

    def run_due(self, now: Optional[float] = None) -> int:
        """Delivers every item whose time has come, oldest first. Returns how many were delivered."""
        current = self._time_fn() if now is None else now
        ready = []
        with self._cond:
            while self._heap and self._heap[0][0] <= current:
                ready.append(heapq.heappop(self._heap)[2])
        for item in ready:
            try:
                self._deliver(item)
            except Exception:
                logger.exception("delayed_dispatch_deliver_failed")
        return len(ready)

    def _loop(self) -> None:
        while True:
            with self._cond:
                if self._stopped:
                    return
                wait = None
                if self._heap:
                    wait = max(0.0, self._heap[0][0] - self._time_fn())
                if wait is None or wait > 0:
                    self._cond.wait(timeout=wait)
                if self._stopped:
                    return
            self.run_due()
