"""Verified SQLite-backed deep-history downloader.

TARGET PATH: D:\QuantumTrade19\engines\workers\market_data\deep_history_downloader_worker.py
REPLACE THE ENTIRE FILE.

FIX v0.4.38 - Gold never downloads (confirmed via direct broker test):
the broker's candles REST endpoint uses "B-XAUT_USDT" for Gold historical
data, not "B-XAU_USDT" (which the WS ticker feed correctly uses). Every
outgoing candles request now passes the symbol through
to_broker_candles_symbol() (engines/workers/market_data/broker_symbol_map.py)
before building the "pair" request parameter. The internal symbol
(B-XAU_USDT) is completely unchanged everywhere else - SQLite storage
key, manifest key, status dict key, on_chunk/on_progress callbacks all
still use the ORIGINAL internal symbol string. Only the literal HTTP
request differs.

FIX v0.4.35 (carried forward) - added reset_status(symbol, timeframe):
clears this worker's own cached status dict for one symbol+timeframe.
market_data_monitor.py's delete_deep_history() calls this immediately
after clearing the manifest and SQLite rows, so a stale "complete/100%"
status can never survive a Delete Data click.

FIX v0.4.19 (carried forward) - CRITICAL INFINITE LOOP FIX: detects when a
gap-fill attempt makes ZERO backward progress and treats it exactly like
an empty response - stopping that gap-fill session cleanly instead of
retrying the same unreachable historical range forever.

v0.4.8 (unchanged): Missing ranges are calculated from physical SQLite
rows. Every remote batch is persisted first, then local coverage is
rechecked. Manifest entries are written only after the storage callback
succeeds.

v0.4.15 (unchanged): real ETA tracking based on observed download rate.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import requests

from engines.workers.market_data.broker_symbol_map import to_broker_candles_symbol
from engines.workers.market_data.candle_builder_worker import Candle
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker

logger = logging.getLogger("market_data.deep_history_downloader")

CANDLES_URL = "https://public.coindcx.com/market_data/candles/"
MAX_LIMIT_PER_CALL = 1000
CHUNK_PACING_S = 0.35
_TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
EARLY_START_MS = 1420070400000
_DAY_MS = 86_400_000


def covered_days(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> float:
    ranges = manifest.get_covered_ranges(symbol, timeframe)
    return round(sum(end - start for start, end in ranges) / _DAY_MS, 1)


def is_fully_downloaded(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> bool:
    return any(start <= EARLY_START_MS + 1 for start, _ in manifest.get_covered_ranges(symbol, timeframe))


def earliest_covered_ms(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> Optional[int]:
    ranges = manifest.get_covered_ranges(symbol, timeframe)
    return min((start for start, _ in ranges), default=None)


class DeepHistoryDownloaderWorker:
    def __init__(
        self,
        manifest: HistoryManifestWorker,
        http_get=None,
        on_chunk: Optional[Callable[[str, str, list[Candle]], None]] = None,
        on_progress: Optional[Callable[[str, str, dict], None]] = None,
        get_missing_ranges: Optional[Callable[[str, str, int, int], list[tuple[int, int]]]] = None,
        get_coverage: Optional[Callable[[str, str, int, int], dict]] = None,
    ) -> None:
        self._manifest = manifest
        self._http_get = http_get or requests.get
        self._on_chunk = on_chunk
        self._on_progress = on_progress
        self._get_missing_ranges = get_missing_ranges
        self._get_coverage = get_coverage
        self._active: dict[tuple[str, str], threading.Event] = {}
        self._status: dict[tuple[str, str], dict] = {}
        self._rate_tracker: dict[tuple[str, str], tuple[float, int]] = {}
        self._lock = threading.RLock()

    def _set_status(self, symbol: str, timeframe: str, **values) -> None:
        with self._lock:
            current = dict(self._status.get((symbol, timeframe), {}))
            current.update(values)
            self._status[(symbol, timeframe)] = current

    def get_status(self, symbol: str, timeframe: str) -> dict:
        with self._lock:
            status = dict(self._status.get((symbol, timeframe), {}))
        return {
            "state": status.get("state", "idle"),
            "error": status.get("error"),
            "requested_days": status.get("requested_days", 0),
            "requested_start_ms": status.get("requested_start_ms"),
            "requested_end_ms": status.get("requested_end_ms"),
            "present_candles": status.get("present_candles", 0),
            "required_candles": status.get("required_candles", 0),
            "missing_candles": status.get("missing_candles", 0),
            "percent": status.get("percent", 0),
            "broker_ceiling_reached": status.get("broker_ceiling_reached", False),
            "eta_seconds": status.get("eta_seconds"),
        }

    def reset_status(self, symbol: str, timeframe: str) -> None:
        """Clears this worker's cached status for one symbol+timeframe back
        to a clean idle state. Called by market_data_monitor.delete_deep_history()
        right after the manifest and physical SQLite rows are cleared."""
        with self._lock:
            self._status.pop((symbol, timeframe), None)
            self._rate_tracker.pop((symbol, timeframe), None)

    def start_download(self, symbol: str, timeframe: str, target_days: Optional[int] = None) -> None:
        key = (symbol, timeframe)
        with self._lock:
            if key in self._active:
                return
            stop_event = threading.Event()
            self._active[key] = stop_event
        with self._lock:
            self._rate_tracker.pop(key, None)
        self._set_status(symbol, timeframe, state="queued", error=None, broker_ceiling_reached=False, eta_seconds=None)
        threading.Thread(
            target=self._download_loop,
            args=(symbol, timeframe, target_days, stop_event),
            daemon=True,
            name=f"QT19History-{symbol}-{timeframe}",
        ).start()

    def cancel_download(self, symbol: str, timeframe: str) -> None:
        with self._lock:
            stop_event = self._active.get((symbol, timeframe))
        if stop_event:
            stop_event.set()
        self._set_status(symbol, timeframe, state="paused", error=None, eta_seconds=None)

    def is_downloading(self, symbol: str, timeframe: str) -> bool:
        with self._lock:
            return (symbol, timeframe) in self._active

    def _estimate_eta_seconds(self, symbol: str, timeframe: str, present: int, missing: int) -> Optional[float]:
        key = (symbol, timeframe)
        now = time.time()
        with self._lock:
            previous = self._rate_tracker.get(key)
            self._rate_tracker[key] = (now, present)
        if previous is None or missing <= 0:
            return None
        prev_ts, prev_present = previous
        elapsed = now - prev_ts
        gained = present - prev_present
        if elapsed <= 0.05 or gained <= 0:
            return None
        rate_per_second = gained / elapsed
        if rate_per_second <= 0:
            return None
        return round(missing / rate_per_second, 1)

    def _emit_progress(self, symbol: str, timeframe: str, start_ms: int, end_ms: int, requested_days: int) -> dict:
        if self._get_coverage:
            coverage = dict(self._get_coverage(symbol, timeframe, start_ms, end_ms))
            required = int(coverage.get("requested_candles", 0))
            present = int(coverage.get("present_candles", 0))
            missing = int(coverage.get("missing_candles", max(0, required - present)))
            complete = bool(coverage.get("requested_range_complete", False))
        else:
            percent_manifest = self._manifest.coverage_percent(symbol, timeframe, start_ms, end_ms)
            required = present = missing = 0
            complete = percent_manifest >= 100.0
            coverage = {"percent": percent_manifest}
        percent = 100 if complete else (int(round((present / required) * 100)) if required else 0)
        eta_seconds = None if complete else self._estimate_eta_seconds(symbol, timeframe, present, missing)
        payload = {
            "state": "complete" if complete else "downloading",
            "requested_days": requested_days,
            "requested_start_ms": start_ms,
            "requested_end_ms": end_ms,
            "present_candles": present,
            "required_candles": required,
            "missing_candles": missing,
            "percent": max(0, min(100, percent)),
            "is_complete": complete,
            "eta_seconds": eta_seconds,
        }
        self._set_status(symbol, timeframe, error=None, **payload)
        if self._on_progress:
            self._on_progress(symbol, timeframe, dict(payload))
        return payload

    def _persist_batch(self, symbol: str, timeframe: str, candles: list[Candle]) -> None:
        if not candles:
            return
        if self._on_chunk is None:
            raise RuntimeError("Deep history downloader has no SQLite persistence callback.")
        self._on_chunk(symbol, timeframe, candles)
        batch_start = min(candle.open_time for candle in candles)
        batch_end = max(candle.open_time for candle in candles) + _TF_MS[timeframe]
        self._manifest.mark_covered(symbol, timeframe, batch_start, batch_end)

    def _fill_one_gap(self, symbol: str, timeframe: str, gap_start: int, gap_end: int, stop_event: threading.Event) -> tuple[bool, bool]:
        """Attempts to fill ONE gap, walking backward from gap_end toward
        gap_start. Returns (received_any, made_progress). The HTTP request
        uses to_broker_candles_symbol(symbol) for the "pair" parameter -
        everything else (candles built, persisted, and returned) still
        uses the original internal `symbol` string."""
        cursor_end = gap_end
        received_any = False
        made_progress = False
        broker_symbol = to_broker_candles_symbol(symbol)
        while not stop_event.is_set() and cursor_end > gap_start:
            response = self._http_get(
                CANDLES_URL,
                params={
                    "pair": broker_symbol,
                    "interval": timeframe,
                    "startTime": gap_start,
                    "endTime": cursor_end,
                    "limit": MAX_LIMIT_PER_CALL,
                },
                timeout=15,
            )
            response.raise_for_status()
            rows = response.json() or []
            if not rows:
                self._set_status(symbol, timeframe, broker_ceiling_reached=True, eta_seconds=None)
                break
            candles = [
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=int(row["time"]),
                    close_time=int(row["time"]) + _TF_MS[timeframe] - 1,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0) or 0.0),
                    is_closed=True,
                )
                for row in rows
                if "time" in row
            ]
            if not candles:
                self._set_status(symbol, timeframe, broker_ceiling_reached=True, eta_seconds=None)
                break

            attempt_started_at = cursor_end
            self._persist_batch(symbol, timeframe, candles)
            received_any = True

            batch_oldest = min(candle.open_time for candle in candles)
            if batch_oldest >= attempt_started_at:
                self._set_status(symbol, timeframe, broker_ceiling_reached=True, eta_seconds=None)
                made_progress = False
                break
            made_progress = True
            if batch_oldest <= gap_start:
                break
            cursor_end = batch_oldest - 1
            time.sleep(CHUNK_PACING_S)
        return received_any, made_progress

    def _download_loop(self, symbol: str, timeframe: str, target_days: Optional[int], stop_event: threading.Event) -> None:
        if timeframe not in _TF_MS:
            self._set_status(symbol, timeframe, state="error", error=f"Unsupported timeframe: {timeframe}")
            with self._lock:
                self._active.pop((symbol, timeframe), None)
            return
        now_ms = int(time.time() * 1000)
        requested_days = max(1, int(target_days or 1))
        start_ms = max(EARLY_START_MS, now_ms - requested_days * _DAY_MS)
        end_ms = now_ms
        self._set_status(
            symbol, timeframe, state="downloading", error=None,
            requested_days=requested_days, requested_start_ms=start_ms, requested_end_ms=end_ms,
        )
        try:
            while not stop_event.is_set():
                progress = self._emit_progress(symbol, timeframe, start_ms, end_ms, requested_days)
                if progress["is_complete"]:
                    break
                if self._get_missing_ranges is None:
                    gaps = self._manifest.find_gaps(symbol, timeframe, start_ms, end_ms)
                else:
                    gaps = self._get_missing_ranges(symbol, timeframe, start_ms, end_ms)
                if not gaps:
                    self._set_status(symbol, timeframe, state="complete", error=None, percent=100, eta_seconds=None)
                    break

                gap_start, gap_end = gaps[-1]
                received_any, made_progress = self._fill_one_gap(symbol, timeframe, gap_start, gap_end, stop_event)

                if not received_any:
                    break
                if not made_progress:
                    break
                if self._emit_progress(symbol, timeframe, start_ms, end_ms, requested_days)["is_complete"]:
                    break
            if stop_event.is_set():
                self._set_status(symbol, timeframe, state="paused", error=None, eta_seconds=None)
            else:
                final = self._emit_progress(symbol, timeframe, start_ms, end_ms, requested_days)
                if final["is_complete"]:
                    self._set_status(symbol, timeframe, state="complete", error=None, percent=100, eta_seconds=None)
                elif self.get_status(symbol, timeframe)["broker_ceiling_reached"]:
                    self._set_status(symbol, timeframe, state="broker_ceiling", error=None, eta_seconds=None)
                else:
                    self._set_status(symbol, timeframe, state="incomplete", error="SQLite range remains incomplete", eta_seconds=None)
        except Exception as exc:
            logger.exception("deep_history_download_failed symbol=%s timeframe=%s", symbol, timeframe)
            self._set_status(symbol, timeframe, state="error", error=str(exc), eta_seconds=None)
        finally:
            with self._lock:
                self._active.pop((symbol, timeframe), None)
                self._rate_tracker.pop((symbol, timeframe), None)
