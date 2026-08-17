"""
FULL PATH: engines/workers/market_data/coindcx_socket_transport.py (REPLACE ENTIRE FILE)

v7: adds mandatory structured transport diagnostics. Retains the confirmed
working curl_cffi Chrome TLS/JA3 impersonation and CoinDCX double-JSON
unwrap behavior. Logs connection lifecycle, Engine.IO close/ping timeouts,
unknown handler-safe frame errors, and reader termination -- never logs
cookies, headers, raw frames, API credentials, or full payloads.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Dict, Optional

from curl_cffi.requests import Session

_ORIGIN = "https://coindcx.com"
_IMPERSONATE = "chrome124"
_PING_SILENCE_TIMEOUT_S = 35.0

logger = logging.getLogger("market_data.coindcx_transport")


class CoinDCXSocketTransport:
    """SocketTransport using curl_cffi Chrome TLS/JA3 impersonation.
    Speaks Engine.IO v4 / Socket.IO v5 over a persistent WebSocket."""

    def __init__(self) -> None:
        self._session: Optional[Session] = None
        self._ws = None
        self._handlers: Dict[str, Callable[[dict], None]] = {}
        self._connected = False
        self._namespace_connected = False
        self._last_ping_ts = 0.0
        self._lock = threading.RLock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

    def connect(self, url: str) -> None:
        ws_url = url if "EIO=" in url else f"{url}/socket.io/?EIO=4&transport=websocket"
        logger.info("transport_connect_requested host=stream.coindcx.com impersonate=%s", _IMPERSONATE)
        try:
            self.disconnect()
            self._session = Session(impersonate=_IMPERSONATE)
            self._ws = self._session.ws_connect(ws_url, headers={"Origin": _ORIGIN})

            data, _ = self._ws.recv()
            self._dispatch_frame(self._decode(data))
            self._send_raw("40")

            self._connected = True
            self._last_ping_ts = time.time()
            self._stop_flag.clear()
            self._reader_thread = threading.Thread(
                target=self._read_loop, name="CoinDCXSocketReader", daemon=True
            )
            self._reader_thread.start()
            logger.info("transport_connected")
        except Exception:
            self._connected = False
            self._namespace_connected = False
            logger.exception("transport_connect_failed")
            raise

    def disconnect(self) -> None:
        was_connected = self._connected or self._ws is not None
        self._stop_flag.set()
        self._connected = False
        self._namespace_connected = False
        try:
            self._send_raw("41")
            self._send_raw("1")
        except Exception:
            pass
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                logger.debug("transport_socket_close_failed", exc_info=True)
        self._ws = None
        if self._session:
            try:
                self._session.close()
            except Exception:
                logger.debug("transport_session_close_failed", exc_info=True)
        self._session = None
        if was_connected:
            logger.info("transport_disconnected")

    def emit(self, event: str, data: dict) -> None:
        logger.debug("transport_emit event=%s", event)
        frame = "42" + json.dumps([event, data])
        self._send_raw(frame)

    def on(self, event: str, handler: Callable[[dict], None]) -> None:
        with self._lock:
            self._handlers[event] = handler
        logger.debug("transport_handler_registered event=%s", event)

    def connected(self) -> bool:
        return self._connected

    @staticmethod
    def _decode(data) -> str:
        return data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else data

    def _send_raw(self, frame: str) -> None:
        with self._lock:
            if not self._ws:
                raise ConnectionError("CoinDCX transport has no active WebSocket")
            self._ws.send_str(frame)

    def _read_loop(self) -> None:
        logger.info("transport_reader_started")
        termination_reason = "stop_requested"
        while not self._stop_flag.is_set():
            try:
                data, _ = self._ws.recv()
            except Exception as exc:
                self._connected = False
                termination_reason = f"recv_error:{type(exc).__name__}"
                logger.warning("transport_reader_recv_failed error=%s", type(exc).__name__, exc_info=True)
                break
            if not data:
                continue
            try:
                self._dispatch_frame(self._decode(data))
            except Exception:
                # A malformed frame must not kill the reader thread silently.
                logger.exception("transport_frame_dispatch_failed")
            if time.time() - self._last_ping_ts > _PING_SILENCE_TIMEOUT_S:
                self._connected = False
                termination_reason = "ping_silence_timeout"
                logger.warning("transport_ping_silence_timeout timeout_s=%s", _PING_SILENCE_TIMEOUT_S)
                break
        logger.info("transport_reader_stopped reason=%s", termination_reason)

    def _dispatch_frame(self, frame: str) -> None:
        if not frame:
            return
        eio_type, payload = frame[0], frame[1:]
        if eio_type == "0":
            return
        if eio_type == "2":
            self._last_ping_ts = time.time()
            self._send_raw("3")
        elif eio_type == "3":
            self._last_ping_ts = time.time()
        elif eio_type == "1":
            self._connected = False
            logger.warning("transport_engineio_close_received")
        elif eio_type == "4":
            self._dispatch_socketio_packet(payload)

    def _dispatch_socketio_packet(self, payload: str) -> None:
        if not payload:
            return
        sio_type, body = payload[0], payload[1:]
        if sio_type == "0":
            self._namespace_connected = True
            logger.info("transport_socketio_namespace_connected")
        elif sio_type == "2":
            try:
                event_name, envelope = json.loads(body)
            except (ValueError, TypeError):
                logger.warning("transport_socketio_event_decode_failed")
                return
            unwrapped = self._unwrap_envelope(envelope)
            with self._lock:
                handler = self._handlers.get(event_name)
            if handler:
                handler(unwrapped)
            else:
                logger.debug("transport_unhandled_event event=%s", event_name)

    @staticmethod
    def _unwrap_envelope(envelope):
        """CoinDCX double-encodes event data as a JSON string."""
        if isinstance(envelope, dict) and isinstance(envelope.get("data"), str):
            try:
                return json.loads(envelope["data"])
            except (ValueError, TypeError):
                return envelope
        return envelope
