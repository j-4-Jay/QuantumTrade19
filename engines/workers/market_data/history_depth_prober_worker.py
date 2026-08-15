"""
FULL PATH: engines/workers/market_data/history_depth_prober_worker.py (REPLACE ENTIRE FILE)

REWRITTEN to use your EXISTING HistoryManifestWorker.mark_covered() instead of
a method that doesn't exist on your real manifest. Probing now feeds discovered
ranges directly into the manifest as it walks back, so a probe run also counts
as real downloaded coverage -- no wasted requests.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import requests

from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker

CANDLES_URL = "https://public.coindcx.com/market_data/candles/"
MAX_LIMIT_PER_CALL = 1000
PROBE_PACING_S = 0.3
EARLY_START_MS = 1420070400000


class HistoryDepthProberWorker:
    def __init__(self, manifest: HistoryManifestWorker, http_get=None,
                 on_progress: Optional[Callable[[str, str, dict], None]] = None) -> None:
        self._manifest = manifest
        self._http_get = http_get or requests.get
        self._on_progress = on_progress
        self._active: dict[tuple, threading.Event] = {}
        self._lock = threading.RLock()
        self._results: dict[tuple, dict] = {}

    def start_probe(self, symbol: str, timeframe: str) -> None:
        key = (symbol, timeframe)
        with self._lock:
            if key in self._active:
                return
            stop_event = threading.Event()
            self._active[key] = stop_event
        t = threading.Thread(target=self._probe_loop, args=(symbol, timeframe, stop_event), daemon=True)
        t.start()

    def is_probing(self, symbol: str, timeframe: str) -> bool:
        with self._lock:
            return (symbol, timeframe) in self._active

    def get_ceiling_days(self, symbol: str, timeframe: str) -> Optional[float]:
        with self._lock:
            result = self._results.get((symbol, timeframe))
        return result["span_days"] if result else None

    def _probe_loop(self, symbol: str, timeframe: str, stop_event: threading.Event) -> None:
        end_ms = int(time.time() * 1000)
        cursor_end = end_ms
        oldest_ms = end_ms
        newest_ms = None

        try:
            while not stop_event.is_set():
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

                batch_oldest = min(int(r["time"]) for r in rows)
                batch_newest = max(int(r["time"]) for r in rows)
                if newest_ms is None:
                    newest_ms = batch_newest
                oldest_ms = min(oldest_ms, batch_oldest)
                self._manifest.mark_covered(symbol, timeframe, batch_oldest, batch_newest)

                if self._on_progress:
                    span_days = (newest_ms - oldest_ms) / (1000 * 60 * 60 * 24)
                    self._on_progress(symbol, timeframe, {"probing": True, "span_days_so_far": round(span_days, 1)})

                if batch_oldest >= cursor_end:
                    break
                cursor_end = batch_oldest - 1
                time.sleep(PROBE_PACING_S)

            span_days = (newest_ms - oldest_ms) / (1000 * 60 * 60 * 24) if newest_ms else 0.0
            with self._lock:
                self._results[(symbol, timeframe)] = {"span_days": round(span_days, 1)}
            if self._on_progress:
                self._on_progress(symbol, timeframe, {"probing": False, "ceiling_days": round(span_days, 1)})
        finally:
            with self._lock:
                self._active.pop((symbol, timeframe), None)
