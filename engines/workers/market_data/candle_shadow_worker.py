"""Shadow observer ONLY. No builder, store, strategy callbacks, REST requests or replay."""
from __future__ import annotations
import logging
import math
from pathlib import Path
import queue
import threading
import time

from engines.workers.market_data.shadow_evidence_log import EvidenceLog

log = logging.getLogger("market_data.candle_shadow")
STEPS = {"1m": 60_000, "5m": 300_000}
FIELDS = ("open", "high", "low", "close", "volume")
OFFSETS = (1000, 3000, 10000)


def candle_values(c):
    return {"symbol": str(c.symbol), "tf": str(c.timeframe), "open_time": int(c.open_time),
            **{k: float(getattr(c, k)) for k in FIELDS}}


def parse(payload, symbols):
    if not isinstance(payload, dict) or payload.get("pr") != "futures":
        return []
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) > 100:
        return []
    out = []
    for row in rows:
        try:
            tf = row.get("duration") or payload.get("i")
            symbol = row.get("pair")
            if tf not in STEPS or symbol not in symbols:
                continue
            if payload.get("i") != tf or payload.get("channel") != f"{symbol}_{tf}-futures":
                continue
            seconds = float(row["open_time"])
            ot = int(round(seconds * 1000))
            if not math.isfinite(seconds) or ot % STEPS[tf] != 0:
                continue
            values = {k: float(row[k]) for k in FIELDS}
            if not all(math.isfinite(v) for v in values.values()):
                continue
            if min(values[k] for k in ("open", "high", "low", "close")) <= 0 or values["volume"] < 0:
                continue
            if not (values["low"] <= min(values["open"], values["close"]) <=
                    max(values["open"], values["close"]) <= values["high"]):
                continue
            ets = payload.get("Ets")
            ets = float(ets) if ets is not None else None
            if ets is not None and not math.isfinite(ets):
                continue
            out.append({"symbol": symbol, "tf": tf, "open_time": ot, **values, "Ets": ets})
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            continue
    return out


def matches(a, b):
    return {k: a[k] == b[k] for k in FIELDS}


class CandleShadowWorker:
    def __init__(self, folder=None, transport_factory=None, sink_factory=EvidenceLog):
        self.folder = folder or Path(__file__).resolve().parents[3] / "Debug" / "CandleShadow"
        self.factory = transport_factory
        self.sink_factory = sink_factory
        self.symbols = set()
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.events = queue.Queue(maxsize=4096)
        self.thread = None
        self.transport = None
        self.latest = {}
        self.issued = set()
        self.sink = None
        self.dropped = 0
        self.rejected = 0
        self.last_rx = 0.0
        self.last_clock = None
        self.epoch = 0

    def start(self, symbols):
        if self.thread and self.thread.is_alive():
            return
        with self.lock:
            self.symbols = set(symbols)
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._run, name="CandleShadowObserver", daemon=True)
        self.thread.start()

    def subscribe(self, symbol):
        with self.lock:
            self.symbols.add(symbol)
        self._enqueue("membership", None)

    def unsubscribe(self, symbol):
        with self.lock:
            self.symbols.discard(symbol)
        self._enqueue("membership", None)

    def observe(self, kind, candle):
        if candle.timeframe in ("1m", "5m", "15m") and self.thread and self.thread.is_alive():
            self._enqueue(kind, candle_values(candle))

    def _enqueue(self, kind, data):
        try:
            self.events.put_nowait((kind, data, int(time.time() * 1000), time.monotonic()))
        except queue.Full:
            self.dropped += 1

    def stop(self):
        self.stop_flag.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.thread and self.thread.is_alive():
            log.warning("shadow_stop_pending observer thread still exiting; no synchronous network wait on app")

    def _write(self, kind, **data):
        if not self.sink.append({"kind": kind, "local_ms": int(time.time()*1000),
                                 "epoch": self.epoch, **data}):
            raise RuntimeError("shadow evidence capacity exhausted; observation stops, no deletion")

    def _handle(self, event):
        kind, data, recv, mono = event
        if kind == "stream":
            with self.lock:
                symbols = set(self.symbols)
            rows = parse(data, symbols)
            if not rows:
                self.rejected += 1
            for c in rows:
                key = (c["symbol"], c["tf"], c["open_time"])
                self.latest[key] = dict(c, received_ms=recv)
                self._write("stream_update", received_ms=recv, candle=c,
                            local_minus_Ets_ms=None if c["Ets"] is None else recv-c["Ets"])
        elif kind in ("current_close", "current_delivery", "reconcile_observation"):
            key = (data["symbol"], data["tf"], data["open_time"])
            observed = self.latest.get(key)
            self._write(kind, received_ms=recv, candle=data, stream_observed=observed,
                        exact_matches=matches(data, observed) if observed else None,
                        reference_final=False)

    def _snapshots(self, now):
        for key, c in list(self.latest.items()):
            boundary = c["open_time"] + STEPS[c["tf"]]
            if now - boundary > 1_800_000:
                del self.latest[key]
                continue
            for offset in OFFSETS:
                marker = (key, offset)
                due = boundary + offset
                if now >= due and marker not in self.issued:
                    self.issued.add(marker)
                    self._write("scheduled_snapshot", offset_ms=offset, scheduled_ms=due,
                                captured_ms=now, lateness_ms=now-due,
                                capture_on_schedule=(0 <= now-due <= 500 and c["received_ms"] <= due),
                                queue_dropped=self.dropped,
                                candle=dict(c), reference_final=False)
        live_keys = set(self.latest)
        self.issued = {m for m in self.issued if m[0] in live_keys}
        if len(self.latest) > 2048:
            raise RuntimeError("shadow symbol/candle capacity exceeded")

    def _disconnect(self):
        t, self.transport = self.transport, None
        if t:
            t.disconnect()

    def _run(self):
        backoff = 1
        joined = set()
        next_connect = 0.0
        try:
            self.sink = self.sink_factory(self.folder)
            self._write("session_start", mode="SHADOW", offsets_ms=OFFSETS,
                        note="observations only; timestamps are not clock synchronization or finality")
            log.info("candle_shadow_started evidence=%s", self.sink.path)
            while not self.stop_flag.is_set():
                mono, wall = time.monotonic(), time.time()
                if self.last_clock:
                    jump = (wall-self.last_clock[0]) - (mono-self.last_clock[1])
                    if abs(jump) > 0.25:
                        self._write("clock_discontinuity", change_ms=jump*1000)
                self.last_clock = (wall, mono)
                with self.lock:
                    desired = set(self.symbols)
                if self.transport and (not self.transport.connected() or mono-self.last_rx > 10):
                    self._write("connection_lost", reason="disconnect_or_no_candle_events_10s")
                    self._disconnect()
                    next_connect = mono + backoff
                    backoff = min(30, backoff*2)
                    joined.clear()
                if desired and not self.transport and mono >= next_connect:
                    try:
                        if self.factory is None:
                            from engines.workers.market_data.coindcx_socket_transport import CoinDCXSocketTransport
                            self.factory = CoinDCXSocketTransport
                        self.transport = self.factory()
                        self.transport.on("candlestick", self._receive)
                        self.transport.connect("wss://stream.coindcx.com")
                        self.last_rx = time.monotonic()
                        self.epoch += 1
                        self.latest.clear()
                        self.issued.clear()
                        self._write("connected", symbols=sorted(desired))
                    except Exception as exc:
                        self._write("connect_error", error_type=type(exc).__name__)
                        self._disconnect()
                        next_connect = time.monotonic()+backoff
                        backoff = min(30, backoff*2)
                if self.transport:
                    for symbol in sorted(joined-desired):
                        for tf in STEPS:
                            self.transport.emit("leave", {"channelName": f"{symbol}_{tf}-futures"})
                    for symbol in sorted(desired-joined):
                        for tf in STEPS:
                            self.transport.emit("join", {"channelName": f"{symbol}_{tf}-futures"})
                    joined = desired
                try:
                    self._handle(self.events.get(timeout=0.1))
                except queue.Empty:
                    pass
                self._snapshots(int(time.time()*1000))
            self._write("session_stop", dropped=self.dropped, rejected=self.rejected)
        except Exception:
            log.exception("candle_shadow_stopped observation failed; current feed unchanged")
        finally:
            try:
                self._disconnect()
            except Exception:
                log.warning("shadow_disconnect_failed", exc_info=True)
            if self.sink:
                self.sink.close()

    def _receive(self, payload):
        self.last_rx = time.monotonic()
        self._enqueue("stream", payload)
