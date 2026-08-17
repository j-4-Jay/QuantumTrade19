"""
FULL PATH: engines/workers/market_data/ws_feed_worker.py (REPLACE ENTIRE FILE)

v4: persistent aggregate-channel reconnect + correct CoinDCX delta handling
+ structured audit logging.

IMPORTANT REAL-FEED DISCOVERY:
The `currentPrices@futures@rt` aggregate stream emits partial per-symbol
DELTAS, not a complete ticker object every update. A symbol row can contain:
  - ls (last price) and/or mp (mark price): usable price-bearing delta -> tick
  - only bmST/cmRT timestamps: metadata-only delta -> NOT a tick, normal
  - None / absent: symbol unchanged in that aggregate delta -> normal
  - v + timestamps but no price: volume-only delta -> NOT a tick, normal

Old code handed every non-None row to TickNormalizerWorker, which correctly
rejected no-price deltas but caused false warning floods. This version:
  1. refreshes the aggregate/channel heartbeat on every valid aggregate frame;
  2. updates each subscribed symbol's liveness heartbeat on every aggregate
     frame (the aggregate channel itself is healthy, even if that symbol did
     not change price in this exact delta);
  3. forwards only price-bearing rows to TickNormalizerWorker;
  4. keeps metadata/absent deltas as DEBUG telemetry only.

ROOT RECONNECT BUG FIXED:
Previous code scheduled only one reconnect attempt after stale detection. If
it failed, symbols remained connected=False forever because the watchdog only
entered its reconnect branch while connected=True. This has one persistent,
connection-level exponential-backoff reconnect loop (1s..30s, never gives up
until stop), restoring symbols only after a real aggregate payload arrives.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol


HEARTBEAT_TIMEOUT_S = 5.0
HEARTBEAT_POLL_INTERVAL_S = 0.5
RECONNECT_BACKOFF_START_S = 1.0
RECONNECT_BACKOFF_MAX_S = 30.0
AGGREGATE_CHANNEL = "currentPrices@futures@rt"
AGGREGATE_UPDATE_EVENT = "currentPrices@futures#update"
AGGREGATE_SNAPSHOT_EVENT = "currentPrices@futures#snapshot"
PRICE_FIELD_CANDIDATES = ("ls", "mp", "p", "price", "last_price", "close", "c")

logger = logging.getLogger("market_data.ws_feed")


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
    def __init__(
        self,
        transport: SocketTransport,
        ws_url: str = "wss://stream.coindcx.com",
        on_tick: Optional[Callable[[str, dict], None]] = None,
        on_drop: Optional[Callable[[str], None]] = None,
        on_restore: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._transport = transport
        self._ws_url = ws_url
        self._on_tick = on_tick
        self._on_drop = on_drop
        self._on_restore = on_restore
        self._lock = threading.RLock()
        self._status: Dict[str, WSStatus] = {}
        self._watchdog_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._reconnect_wakeup = threading.Event()
        self._channel_joined = False
        self._last_aggregate_ts = 0.0

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self._stop_flag.clear()
        logger.info("ws_start_requested url=%s channel=%s", self._ws_url, AGGREGATE_CHANNEL)
        self._connect_and_join(reason="startup")

        with self._lock:
            if not self._watchdog_thread or not self._watchdog_thread.is_alive():
                self._watchdog_thread = threading.Thread(
                    target=self._watchdog_loop, name="WSFeedWatchdog", daemon=True
                )
                self._watchdog_thread.start()
            if not self._reconnect_thread or not self._reconnect_thread.is_alive():
                self._reconnect_thread = threading.Thread(
                    target=self._reconnect_loop, name="WSFeedReconnect", daemon=True
                )
                self._reconnect_thread.start()

    def stop(self) -> None:
        logger.info("ws_stop_requested")
        self._stop_flag.set()
        self._reconnect_wakeup.set()
        self._mark_all_disconnected(reason="stop", notify_drop=False)
        try:
            self._transport.disconnect()
        except Exception:
            logger.warning("ws_disconnect_error_during_stop", exc_info=True)

    def subscribe(self, symbol: str) -> None:
        """Aggregate channel is shared; tracking/liveness is per symbol."""
        now = time.time()
        with self._lock:
            aggregate_alive = bool(
                self._channel_joined and self._transport.connected() and
                now - self._last_aggregate_ts <= HEARTBEAT_TIMEOUT_S
            )
            self._status[symbol] = WSStatus(connected=aggregate_alive, last_message_ts=now)
        logger.info("ws_symbol_subscribed symbol=%s aggregate_alive=%s", symbol, aggregate_alive)
        if not aggregate_alive:
            self._reconnect_wakeup.set()

    def unsubscribe(self, symbol: str) -> None:
        with self._lock:
            existed = self._status.pop(symbol, None) is not None
        if existed:
            logger.info("ws_symbol_unsubscribed symbol=%s", symbol)

    # ------------------------------------------------------------------ transport connection
    def _connect_and_join(self, reason: str) -> bool:
        """Connection-level operation. A joined socket is not treated as
        healthy until a real aggregate event is received."""
        try:
            if self._transport.connected():
                try:
                    self._transport.disconnect()
                except Exception:
                    logger.debug("ws_preconnect_cleanup_failed", exc_info=True)

            self._transport.connect(self._ws_url)
            self._transport.on(AGGREGATE_UPDATE_EVENT, self._handle_aggregate_payload)
            self._transport.on(AGGREGATE_SNAPSHOT_EVENT, self._handle_aggregate_payload)
            self._transport.emit("join", {"channelName": AGGREGATE_CHANNEL})
            with self._lock:
                self._channel_joined = True
                self._last_aggregate_ts = 0.0
            logger.info("ws_connected_joined reason=%s channel=%s", reason, AGGREGATE_CHANNEL)
            return True
        except Exception:
            with self._lock:
                self._channel_joined = False
            logger.exception("ws_connect_or_join_failed reason=%s", reason)
            return False

    # ------------------------------------------------------------------ aggregate delta path
    def _handle_aggregate_payload(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            logger.warning("ws_invalid_aggregate_payload type=%s", type(payload).__name__)
            return
        prices = payload.get("prices")
        if not isinstance(prices, dict):
            logger.warning("ws_aggregate_payload_missing_prices keys=%s", list(payload.keys())[:10])
            return

        now = time.time()
        with self._lock:
            self._last_aggregate_ts = now
            tracked_symbols = list(self._status.keys())

        price_bearing_count = 0
        metadata_only_count = 0
        absent_count = 0

        for symbol in tracked_symbols:
            row = prices.get(symbol)
            if row is None:
                absent_count += 1
                self._mark_symbol_channel_alive(symbol, now)
                continue

            if not isinstance(row, dict):
                metadata_only_count += 1
                self._mark_symbol_channel_alive(symbol, now)
                logger.debug("ws_non_dict_delta_ignored symbol=%s type=%s", symbol, type(row).__name__)
                continue

            if not self._has_usable_price(row):
                metadata_only_count += 1
                self._mark_symbol_channel_alive(symbol, now)
                logger.debug("ws_metadata_delta_ignored symbol=%s keys=%s", symbol, sorted(row.keys()))
                continue

            price_bearing_count += 1
            self._handle_price_delta(symbol, row, now)

        # Approx. 2 events/sec: DEBUG only, never flood INFO/WARNING logs.
        logger.debug(
            "ws_aggregate_processed tracked=%d price_bearing=%d metadata_only=%d absent=%d",
            len(tracked_symbols), price_bearing_count, metadata_only_count, absent_count,
        )

    @staticmethod
    def _has_usable_price(row: dict) -> bool:
        """A price-bearing delta has at least one parseable positive candidate.
        `mp` is valid as fallback when `ls` did not change in this delta."""
        for field in PRICE_FIELD_CANDIDATES:
            value = row.get(field)
            if value in (None, ""):
                continue
            try:
                if float(value) > 0:
                    return True
            except (TypeError, ValueError):
                continue
        return False

    def _mark_symbol_channel_alive(self, symbol: str, now: float) -> None:
        """A metadata/absent delta does not create a price tick, but it proves
        the aggregate channel is still alive. It must therefore prevent a
        false WS timeout/fallback activation for this subscribed symbol."""
        with self._lock:
            st = self._status.get(symbol)
            if st is None:
                return
            was_down = not st.connected
            st.connected = True
            st.last_message_ts = now
            st.reconnect_attempts = 0

        if was_down:
            logger.info("ws_symbol_restored symbol=%s restore_source=aggregate_heartbeat", symbol)
            if self._on_restore:
                try:
                    self._on_restore(symbol)
                except Exception:
                    logger.exception("ws_on_restore_callback_failed symbol=%s", symbol)

    def _handle_price_delta(self, symbol: str, raw_row: dict, now: float) -> None:
        with self._lock:
            st = self._status.setdefault(symbol, WSStatus())
            was_down = not st.connected
            st.connected = True
            st.last_message_ts = now
            st.reconnect_attempts = 0

        if was_down:
            logger.info("ws_symbol_restored symbol=%s restore_source=price_delta", symbol)
            if self._on_restore:
                try:
                    self._on_restore(symbol)
                except Exception:
                    logger.exception("ws_on_restore_callback_failed symbol=%s", symbol)

        if self._on_tick:
            try:
                self._on_tick(symbol, raw_row)
            except Exception:
                logger.exception("ws_on_tick_callback_failed symbol=%s", symbol)

    # ------------------------------------------------------------------ watchdog / reconnection
    def _watchdog_loop(self) -> None:
        logger.info("ws_watchdog_started timeout_s=%s", HEARTBEAT_TIMEOUT_S)
        while not self._stop_flag.is_set():
            now = time.time()
            stale_symbols = []
            with self._lock:
                aggregate_stale = (
                    not self._channel_joined or
                    not self._transport.connected() or
                    now - self._last_aggregate_ts > HEARTBEAT_TIMEOUT_S
                )
                if aggregate_stale:
                    for symbol, st in self._status.items():
                        if st.connected:
                            st.connected = False
                            stale_symbols.append(symbol)

            for symbol in stale_symbols:
                logger.warning("ws_symbol_stale symbol=%s timeout_s=%s", symbol, HEARTBEAT_TIMEOUT_S)
                if self._on_drop:
                    try:
                        self._on_drop(symbol)
                    except Exception:
                        logger.exception("ws_on_drop_callback_failed symbol=%s", symbol)

            if stale_symbols or not self._transport.connected() or not self._channel_joined:
                self._reconnect_wakeup.set()

            self._stop_flag.wait(HEARTBEAT_POLL_INTERVAL_S)
        logger.info("ws_watchdog_stopped")

    def _reconnect_loop(self) -> None:
        """Persistent connection-level retry loop. It never abandons recovery
        while the worker is running; capped exponential backoff avoids hammering
        the gateway during outages."""
        attempt = 0
        logger.info("ws_reconnect_loop_started")
        while not self._stop_flag.is_set():
            self._reconnect_wakeup.wait(timeout=HEARTBEAT_POLL_INTERVAL_S)
            if self._stop_flag.is_set():
                break

            with self._lock:
                needs_reconnect = bool(self._status) and (
                    not self._channel_joined or
                    not self._transport.connected() or
                    any(not st.connected for st in self._status.values())
                )
            if not needs_reconnect:
                self._reconnect_wakeup.clear()
                attempt = 0
                continue

            backoff = min(RECONNECT_BACKOFF_START_S * (2 ** attempt), RECONNECT_BACKOFF_MAX_S)
            logger.warning("ws_reconnect_scheduled attempt=%d backoff_s=%.1f", attempt + 1, backoff)
            if self._stop_flag.wait(backoff):
                break

            success = self._connect_and_join(reason="watchdog_reconnect")
            with self._lock:
                for st in self._status.values():
                    st.reconnect_attempts = attempt + 1

            if success:
                logger.info("ws_reconnect_transport_success awaiting_aggregate_payload=true")
                # The reconnect wakeup is cleared; watchdog will re-pulse it if
                # no aggregate heartbeat arrives in HEARTBEAT_TIMEOUT_S.
                self._reconnect_wakeup.clear()
                attempt = 0
            else:
                attempt = min(attempt + 1, 30)
                self._reconnect_wakeup.set()

        logger.info("ws_reconnect_loop_stopped")

    def _mark_all_disconnected(self, reason: str, notify_drop: bool) -> None:
        with self._lock:
            symbols_to_notify = []
            self._channel_joined = False
            self._last_aggregate_ts = 0.0
            for symbol, st in self._status.items():
                if st.connected:
                    st.connected = False
                    if notify_drop:
                        symbols_to_notify.append(symbol)
        for symbol in symbols_to_notify:
            logger.warning("ws_symbol_dropped symbol=%s reason=%s", symbol, reason)
            if self._on_drop:
                try:
                    self._on_drop(symbol)
                except Exception:
                    logger.exception("ws_on_drop_callback_failed symbol=%s", symbol)

    # ------------------------------------------------------------------ public status interface
    def get_status(self, symbol: str) -> Optional[WSStatus]:
        with self._lock:
            return self._status.get(symbol)

    def is_healthy(self, symbol: str) -> bool:
        st = self.get_status(symbol)
        return bool(st and st.connected)
