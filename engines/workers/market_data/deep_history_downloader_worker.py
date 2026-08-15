"""
FULL PATH: engines/workers/market_data/deep_history_downloader_worker.py (REPLACE ENTIRE FILE)

REWRITTEN to use your EXISTING HistoryManifestWorker API (get_covered_ranges,
mark_covered, find_gaps, coverage_percent, delete_symbol_manifest) instead of
methods that don't exist on your real manifest file.

"True earliest reached" is now inferred, not separately tracked: when the API
returns an empty page, we mark_covered(symbol, tf, EARLY_START_MS, cursor_end)
-- i.e. "nothing exists before this point" becomes part of the covered range
itself. That merges with real data ranges automatically (your manifest's own
merge logic), so a fully-covered range starting at/near EARLY_START_MS IS the
signal that the true earliest has been reached -- no extra flag needed.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import requests

from engines.workers.market_data.candle_builder_worker import Candle
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker

CANDLES_URL = "https://public.coindcx.com/market_data/candles/"
MAX_LIMIT_PER_CALL = 1000
CHUNK_PACING_S = 0.35
_TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
EARLY_START_MS = 1420070400000  # 2015-01-01 UTC, our "search floor"


def covered_days(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> float:
    ranges = manifest.get_covered_ranges(symbol, timeframe)
    total_ms = sum(end - start for start, end in ranges)
    return round(total_ms / (1000 * 60 * 60 * 24), 1)


def is_fully_downloaded(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> bool:
    ranges = manifest.get_covered_ranges(symbol, timeframe)
    return any(start <= EARLY_START_MS + 1 for start, _ in ranges)


def earliest_covered_ms(manifest: HistoryManifestWorker, symbol: str, timeframe: str) -> Optional[int]:
    ranges = manifest.get_covered_ranges(symbol, timeframe)
    if not ranges:
        return None
    return min(start for start, _ in ranges)


class DeepHistoryDownloaderWorker:
    def __init__(self, manifest: HistoryManifestWorker, http_get=None,
                 on_chunk: Optional[Callable[[str, str, list], None]] = None,
                 on_progress: Optional[Callable[[str, str, dict], None]] = None) -> None:
        self._manifest = manifest
        self._http_get = http_get or requests.get
        self._on_chunk = on_chunk
        self._on_progress = on_progress
        self._active: dict[tuple, threading.Event] = {}
        self._lock = threading.RLock()

    def start_download(self, symbol: str, timeframe: str, target_days: Optional[int] = None) -> None:
        key = (symbol, timeframe)
        with self._lock:
            if key in self._active:
                return
            stop_event = threading.Event()
            self._active[key] = stop_event
        t = threading.Thread(target=self._download_loop, args=(symbol, timeframe, target_days, stop_event), daemon=True)
        t.start()

    def cancel_download(self, symbol: str, timeframe: str) -> None:
        with self._lock:
            stop_event = self._active.pop((symbol, timeframe), None)
            if stop_event:
                stop_event.set()

    def is_downloading(self, symbol: str, timeframe: str) -> bool:
        with self._lock:
            return (symbol, timeframe) in self._active

    def _download_loop(self, symbol: str, timeframe: str, target_days: Optional[int], stop_event: threading.Event) -> None:
        try:
            earliest = earliest_covered_ms(self._manifest, symbol, timeframe)
            cursor_end = (earliest - 1) if earliest else int(time.time() * 1000)

            while not stop_event.is_set():
                if is_fully_downloaded(self._manifest, symbol, timeframe):
                    break
                if target_days is not None and covered_days(self._manifest, symbol, timeframe) >= target_days:
                    break

                resp = self._http_get(CANDLES_URL, params={
                    "pair": symbol, "interval": timeframe,
                    "startTime": EARLY_START_MS, "endTime": cursor_end,
                    "limit": MAX_LIMIT_PER_CALL,
                }, timeout=10)
                resp.raise_for_status()
                rows = resp.json() or []

                if not rows:
                    self._manifest.mark_covered(symbol, timeframe, EARLY_START_MS, cursor_end)
                    break

                candles = [Candle(
                    symbol=symbol, timeframe=timeframe,
                    open_time=int(r["time"]), close_time=int(r["time"]) + _TF_MS[timeframe] - 1,
                    open=float(r["open"]), high=float(r["high"]), low=float(r["low"]),
                    close=float(r["close"]), volume=float(r.get("volume", 0.0) or 0.0), is_closed=True,
                ) for r in rows]

                batch_oldest = min(c.open_time for c in candles)
                batch_newest = max(c.open_time for c in candles)
                self._manifest.mark_covered(symbol, timeframe, batch_oldest, batch_newest)

                if self._on_chunk:
                    self._on_chunk(symbol, timeframe, candles)
                if self._on_progress:
                    self._on_progress(symbol, timeframe, {
                        "covered_days": covered_days(self._manifest, symbol, timeframe),
                        "is_complete": is_fully_downloaded(self._manifest, symbol, timeframe),
                    })

                if batch_oldest >= cursor_end:
                    break
                cursor_end = batch_oldest - 1
                time.sleep(CHUNK_PACING_S)
        finally:
            with self._lock:
                self._active.pop((symbol, timeframe), None)
