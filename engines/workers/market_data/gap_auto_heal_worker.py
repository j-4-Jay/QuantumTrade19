"""Background auto-heal + auto-probe worker: continuously scans local SQLite
coverage for existing gaps and refills them slowly in bounded chunks, and
periodically re-probes the broker ceiling - all fully automatic, independent
of any browser session.

PATH: engines/workers/market_data/gap_auto_heal_worker.py  (REPLACE ENTIRE FILE)

CHANGE v0.4.15: added automatic periodic broker-ceiling probing. Previously
the broker ceiling was only probed once, manually, or via a one-time
Reflex on_load event - stale forever after that unless a user clicked
Probe. This worker now fires a probe for every active symbol/TF the moment
it starts (replacing the old one-time UI-triggered startup scan entirely -
see core_shell_mixin.py and deep_history_card_mixin.py's matching v0.4.15
changes, which remove that redundant UI-side trigger), and again every
_PROBE_INTERVAL_S seconds thereafter, so the ceiling reference never goes
stale without requiring any user action. A manual Probe button remains
available in the UI as an optional override, but is no longer required.

v0.4.14 (unchanged): gap auto-heal. Every _SCAN_INTERVAL_S seconds, checks
every active symbol x every configured timeframe for an existing internal
gap (2+ physical SQLite ranges) and, only if that TF is not already
downloading, triggers ONE bounded heal download covering just that TF's own
existing earliest-to-latest span - never expanding beyond what a human
already downloaded. Each symbol/TF is healed completely independently -
DeepHistoryDownloaderWorker keys all of its state by (symbol, timeframe),
so healing one symbol/TF never affects any other symbol's download.
Downloaded candles are only ever removed by an explicit user Delete action
elsewhere - this worker never deletes data.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from typing import Callable, Iterable, Optional

logger = logging.getLogger("market_data.gap_auto_heal")

_DAY_MS = 86_400_000
_SCAN_INTERVAL_S = 60.0
_PROBE_INTERVAL_S = 1800.0  # re-probe broker ceiling every 30 minutes


class GapAutoHealWorker:
    def __init__(
        self,
        get_active_symbols: Callable[[], Iterable[str]],
        get_physical_ranges: Callable[[str, str], list[tuple[int, int]]],
        is_downloading: Callable[[str, str], bool],
        start_download: Callable[[str, str, int], None],
        start_ceiling_probe: Callable[[str, str], None],
        timeframes: Iterable[str],
        scan_interval_s: float = _SCAN_INTERVAL_S,
        probe_interval_s: float = _PROBE_INTERVAL_S,
    ) -> None:
        self._get_active_symbols = get_active_symbols
        self._get_physical_ranges = get_physical_ranges
        self._is_downloading = is_downloading
        self._start_download = start_download
        self._start_ceiling_probe = start_ceiling_probe
        self._timeframes = list(timeframes)
        self._scan_interval_s = scan_interval_s
        self._probe_every_n_scans = max(1, round(probe_interval_s / scan_interval_s))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="QT19GapAutoHeal")
        self._thread.start()
        logger.info(
            "gap_auto_heal_started scan_interval_s=%.1f probe_every_n_scans=%d timeframes=%s",
            self._scan_interval_s, self._probe_every_n_scans, self._timeframes,
        )

    def stop(self) -> None:
        self._stop_event.set()

    def heal_now(self, symbol: str, timeframe: str) -> bool:
        """Immediate bounded heal for one symbol/TF - used by the periodic
        scan. Returns True if a heal download was actually started."""
        if self._is_downloading(symbol, timeframe):
            return False
        ranges = self._get_physical_ranges(symbol, timeframe)
        if len(ranges) < 2:
            return False
        earliest = ranges[0][0]
        now_ms = int(time.time() * 1000)
        span_days = max(1, math.ceil((now_ms - earliest) / _DAY_MS))
        self._start_download(symbol, timeframe, span_days)
        logger.info("gap_auto_heal_triggered symbol=%s timeframe=%s span_days=%d", symbol, timeframe, span_days)
        return True

    def _run(self) -> None:
        scan_count = 0
        while not self._stop_event.is_set():
            try:
                should_probe = (scan_count % self._probe_every_n_scans == 0)
                for symbol in list(self._get_active_symbols()):
                    for timeframe in self._timeframes:
                        if self._stop_event.is_set():
                            return
                        if should_probe:
                            try:
                                self._start_ceiling_probe(symbol, timeframe)
                            except Exception:
                                logger.exception("gap_auto_heal_probe_failed symbol=%s timeframe=%s", symbol, timeframe)
                        self.heal_now(symbol, timeframe)
            except Exception:
                logger.exception("gap_auto_heal_scan_failed")
            scan_count += 1
            self._stop_event.wait(self._scan_interval_s)
