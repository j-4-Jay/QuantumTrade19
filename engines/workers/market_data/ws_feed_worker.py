"""
FULL PATH: engines/workers/market_data/ws_feed_worker.py (REPLACE ENTIRE FILE)

v2: REDESIGNED around confirmed real CoinDCX behavior. There is no working
per-symbol channel with a symbol-tagged event -- the real, usable channel is
the AGGREGATED "currentPrices@futures@rt" channel, which fires
"currentPrices@futures#update" / "...#snapshot" events carrying EVERY
symbol's price in one shared "prices" dict. This worker now joins that one
channel ONCE and demuxes ticks per subscribed symbol internally, instead of
opening a separate channel join per symbol.

Public interface (start/stop/subscribe/unsubscribe/get_status/is_healthy)
is UNCHANGED -- MarketDataMonitor needs zero changes for this fix.
"""
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol

HEARTBEAT_TIMEOUT_S = 5.0  # aggregated channel updates ~2x/sec; allow margin
HEARTBEAT_POLL_INTERVAL_S = 0.5
RECONNECT_BACKOFF_START_S = 1.0
RECONNECT_BACKOFF_MAX_S = 30.0
AGGREGATE_CHANNEL = "currentPrices@futures@rt"
AGGREGATE_UPDATE_EVENT = "currentPrices@futures#update"
AGGREGATE_SNAPSHOT_EVENT = "currentPrices@futures#snapshot"
_PRICE_FIELD_CANDIDATES = ("ls", "mp", "last_price", "price", "close", "c")


class SocketTransport(Protocol):
    def connect(self, url: str) -> None: ...
    def disconnect(self) -> None: ...
    def emit(self, event: str, data: dict) -> None: ...
    def on(self, event: str, handler) -> None: ...
    def connected(self) -> bool: ...


@dataclass
class WSStatus:
    connected: bool = False
    last_message_ts: float = 0.0
    reconnect_attempts: int = 0


class WSFeedWorker:
    def __init__(self, transport, ws_url="wss://stream.coindcx.com", on_tick=None, on_drop=None, on_restore=None):
        self._transport = transport
        self._ws_url = ws_url
        self._on_tick = on_tick
        self._on_drop = on_drop
        self._on_restore = on_restore
        self._lock = threading.RLock()
        self._status: Dict[str, WSStatus] = {}
        self._watchdog_thread = None
        self._stop_flag = threading.Event()
        self._channel_joined = False

    def start(self):
        try:
            self._transport.connect(self._ws_url)
            self._transport.on(AGGREGATE_UPDATE_EVENT, self._handle_aggregate_payload)
            self._transport.on(AGGREGATE_SNAPSHOT_EVENT, self._handle_aggregate_payload)
            self._transport.emit("join", {"channelName": AGGREGATE_CHANNEL})
            self._channel_joined = True
        except Exception:
            self._channel_joined = False
        self._stop_flag.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def stop(self):
        self._stop_flag.set()
        self._transport.disconnect()

    def subscribe(self, symbol):
        """No per-symbol channel join needed -- the aggregated channel
        already carries every symbol. Just start tracking this symbol's
        heartbeat so get_health()/watchdog can detect staleness."""
        with self._lock:
            self._status[symbol] = WSStatus(connected=self._channel_joined, last_message_ts=time.time())

    def unsubscribe(self, symbol):
        with self._lock:
            self._status.pop(symbol, None)

    def _handle_aggregate_payload(self, payload: dict) -> None:
        """payload is already fully unwrapped by CoinDCXSocketTransport into
        a plain dict shaped like {"ts":..., "vs":..., "prices": {symbol: {...}}}."""
        if not isinstance(payload, dict):
            return
        prices = payload.get("prices")
        if not isinstance(prices, dict):
            return
        with self._lock:
            tracked_symbols = list(self._status.keys())
        for symbol in tracked_symbols:
            row = prices.get(symbol)
            if row is None:
                continue
            self._handle_raw_message(symbol, row)

    def _handle_raw_message(self, symbol, raw_row: dict):
        with self._lock:
            st = self._status.setdefault(symbol, WSStatus())
            was_down = not st.connected
            st.connected = True
            st.last_message_ts = time.time()
            st.reconnect_attempts = 0
        if was_down and self._on_restore:
            self._on_restore(symbol)
        if self._on_tick:
            self._on_tick(symbol, raw_row)

    def _watchdog_loop(self):
        while not self._stop_flag.is_set():
            now = time.time()
            with self._lock:
                symbols = list(self._status.items())
            for symbol, st in symbols:
                if st.connected and (now - st.last_message_ts) > HEARTBEAT_TIMEOUT_S:
                    with self._lock:
                        self._status[symbol].connected = False
                    if self._on_drop:
                        self._on_drop(symbol)
                    self._try_reconnect(symbol)
            time.sleep(HEARTBEAT_POLL_INTERVAL_S)

    def _try_reconnect(self, symbol):
        with self._lock:
            attempts = self._status[symbol].reconnect_attempts
        backoff = min(RECONNECT_BACKOFF_START_S * (2 ** attempts), RECONNECT_BACKOFF_MAX_S)

        def _attempt():
            time.sleep(backoff)
            if self._stop_flag.is_set():
                return
            try:
                if not self._transport.connected():
                    self._transport.connect(self._ws_url)
                    self._transport.on(AGGREGATE_UPDATE_EVENT, self._handle_aggregate_payload)
                    self._transport.on(AGGREGATE_SNAPSHOT_EVENT, self._handle_aggregate_payload)
                    self._transport.emit("join", {"channelName": AGGREGATE_CHANNEL})
                    self._channel_joined = True
            except Exception:
                with self._lock:
                    if symbol in self._status:
                        self._status[symbol].reconnect_attempts += 1

        threading.Thread(target=_attempt, daemon=True).start()

    def get_status(self, symbol):
        with self._lock:
            return self._status.get(symbol)

    def is_healthy(self, symbol):
        st = self.get_status(symbol)
        return bool(st and st.connected)
