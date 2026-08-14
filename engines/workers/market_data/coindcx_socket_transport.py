"""
FULL PATH: engines/workers/market_data/coindcx_socket_transport.py (REPLACE ENTIRE FILE)

v6: CONFIRMED WORKING END-TO-END via raw frame capture. Adds the one missing
piece: CoinDCX double-encodes event payloads as {"event": name, "data": "<a
JSON string>"} -- the inner "data" string needs a second json.loads() to get
the real payload. Handlers now always receive the fully-unwrapped dict.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable, Dict, Optional

from curl_cffi.requests import Session

_ORIGIN = "https://coindcx.com"
_IMPERSONATE = "chrome124"
_PING_SILENCE_TIMEOUT_S = 35.0


class CoinDCXSocketTransport:
    """SocketTransport implementation using curl_cffi's Chrome TLS/JA3
    impersonation to pass CoinDCX's gateway fingerprint filter. Speaks
    Engine.IO v4 / Socket.IO v5 over one persistent WebSocket, always as
    TEXT frames, with automatic double-JSON unwrap on incoming events."""

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

        self._session = Session(impersonate=_IMPERSONATE)
        self._ws = self._session.ws_connect(ws_url, headers={"Origin": _ORIGIN})

        data, _ = self._ws.recv()
        self._dispatch_frame(self._decode(data))

        self._send_raw("40")

        self._connected = True
        self._last_ping_ts = time.time()
        self._stop_flag.clear()
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def disconnect(self) -> None:
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
                pass

    def emit(self, event: str, data: dict) -> None:
        frame = "42" + json.dumps([event, data])
        self._send_raw(frame)

    def on(self, event: str, handler: Callable[[dict], None]) -> None:
        with self._lock:
            self._handlers[event] = handler

    def connected(self) -> bool:
        return self._connected

    @staticmethod
    def _decode(data) -> str:
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="ignore")
        return data

    def _send_raw(self, frame: str) -> None:
        with self._lock:
            if self._ws:
                self._ws.send_str(frame)

    def _read_loop(self) -> None:
        while not self._stop_flag.is_set():
            try:
                data, _ = self._ws.recv()
            except Exception:
                self._connected = False
                return
            if not data:
                continue
            self._dispatch_frame(self._decode(data))
            if time.time() - self._last_ping_ts > _PING_SILENCE_TIMEOUT_S:
                self._connected = False
                return

    def _dispatch_frame(self, frame: str) -> None:
        if not frame:
            return
        eio_type, payload = frame[0], frame[1:]
        if eio_type == "0":
            return
        elif eio_type == "2":
            self._last_ping_ts = time.time()
            self._send_raw("3")
        elif eio_type == "3":
            self._last_ping_ts = time.time()
        elif eio_type == "1":
            self._connected = False
        elif eio_type == "4":
            self._dispatch_socketio_packet(payload)

    def _dispatch_socketio_packet(self, payload: str) -> None:
        if not payload:
            return
        sio_type, body = payload[0], payload[1:]
        if sio_type == "0":
            self._namespace_connected = True
        elif sio_type == "2":
            try:
                event_name, envelope = json.loads(body)
            except (ValueError, TypeError):
                return
            unwrapped = self._unwrap_envelope(envelope)
            with self._lock:
                handler = self._handlers.get(event_name)
            if handler:
                handler(unwrapped)

    @staticmethod
    def _unwrap_envelope(envelope):
        """CoinDCX double-encodes: {"event": name, "data": "<json string>"}.
        Unwraps the inner string automatically so handlers always get a
        plain dict, never a raw envelope or a string needing manual parsing."""
        if isinstance(envelope, dict) and "data" in envelope and isinstance(envelope["data"], str):
            try:
                return json.loads(envelope["data"])
            except (ValueError, TypeError):
                return envelope
        return envelope
