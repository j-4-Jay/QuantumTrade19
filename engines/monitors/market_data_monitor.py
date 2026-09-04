"""Market Data Monitor (Tier 2 Assembly).

TARGET PATH: D:\QuantumTrade19\engines\monitors\market_data_monitor.py
REPLACE THE ENTIRE FILE.

FIX v0.4.35 - Deep Historical Data card progress bar stays green/100%
forever after clicking Delete:

delete_deep_history() cleared the manifest and the physical SQLite rows,
but never reset DeepHistoryDownloaderWorker's own in-memory status cache
(percent, state, present/required/missing candles) for that symbol+
timeframe. get_deep_history_progress() reads percent/state directly from
that cached status dict (self.deep_history_downloader.get_status()) - it
is NOT recomputed from physical rows on every call. So after a delete, the
UI kept displaying the last cached "complete/100%" value even though the
database was empty, because nothing ever told the downloader its own
cached status was now stale.

Fix: delete_deep_history() now also calls
self.deep_history_downloader.reset_status(symbol, timeframe) (new method,
added to deep_history_downloader_worker.py in this same patch) immediately
after clearing the manifest and SQLite rows. The next
get_deep_history_progress() call for that symbol/timeframe now correctly
reports state="idle", percent=0, until a new download is started.

NOTE (not a bug - explained, not "fixed"): the Trading Panel chart still
showing some candles immediately after Delete Data is BY DESIGN. Delete
Data only clears the persistent SQLite deep-history archive - it
deliberately does NOT touch CandleBuilderWorker's separate in-memory
baseline window (the always-on minimum-5-day rolling window), per the
project's own Deep Historical Data spec ("Delete Data removes the deep
archive only, 5-day minimum re-downloads automatically if needed").
get_chart_candles() merges both sources on purpose.

FIX v0.4.21 (carried forward, unchanged) - DeepHistoryDownloaderWorker is
wired with get_missing_ranges=self.candle_store.get_missing_ranges and
get_coverage=self.sqlite_coverage_payload (both backed by real SQLite
rows). get_deep_history_progress() returns the full real-time status from
DeepHistoryDownloaderWorker.get_status() - percent, present_candles,
required_candles, missing_candles, eta_seconds, broker_ceiling_reached -
plus physical SQLite coverage.

Everything else - WS/REST/health-report logic, get_historical_candles(),
chart candle merging - is unchanged from v0.3.9.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.ws_feed_worker import WSFeedWorker, SocketTransport
from engines.workers.market_data.rest_poll_fallback_worker import RestPollFallbackWorker
from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker
from engines.workers.market_data.candle_builder_worker import (
    CandleBuilderWorker,
    Candle,
    TRADING_TFS,
    POI_TFS,
)
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.deep_history_downloader_worker import DeepHistoryDownloaderWorker
from engines.workers.market_data.history_depth_prober_worker import HistoryDepthProberWorker
from engines.workers.market_data.candle_store_worker import CandleStoreWorker

logger = logging.getLogger("market_data.monitor")

DAY_MS = 86_400_000


class MarketDataMonitor:
    def __init__(self, transport: SocketTransport) -> None:
        self._lock = threading.RLock()

        self.symbol_registry = SymbolRegistryWorker()
        self.candle_builder = CandleBuilderWorker(on_candle_closed=self._publish_candle_closed)
        self.historical_loader = HistoricalDataLoaderWorker()
        self.rest_fallback = RestPollFallbackWorker(on_tick=self._handle_rest_tick)
        self.ws_feed = WSFeedWorker(
            transport=transport,
            on_tick=self._handle_ws_tick,
            on_drop=self._handle_ws_drop,
            on_restore=self._handle_ws_restore,
        )

        self.history_manifest = HistoryManifestWorker()
        self.candle_store = CandleStoreWorker()
        self.deep_history_downloader = DeepHistoryDownloaderWorker(
            manifest=self.history_manifest,
            on_chunk=self._handle_deep_history_chunk,
            get_missing_ranges=self.candle_store.get_missing_ranges,
            get_coverage=self.sqlite_coverage_payload,
        )
        self.depth_prober = HistoryDepthProberWorker(manifest=self.history_manifest)

        self._subscribed: set[str] = set()
        self._degraded: set[str] = set()
        self._last_health: Dict[str, str] = {}
        logger.info("market_data_monitor_created")

    # ================= public interface =================

    def start(self) -> None:
        active_symbols = self.symbol_registry.get_active_symbols()
        logger.info("market_data_monitor_start active_symbols=%s", active_symbols)
        self.ws_feed.start()
        for symbol in active_symbols:
            self.subscribe(symbol)

    def stop(self) -> None:
        logger.info("market_data_monitor_stop subscribed_count=%d", len(self._subscribed))
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            self.unsubscribe(symbol)
        self.ws_feed.stop()

    def subscribe(self, symbol: str) -> None:
        with self._lock:
            if symbol in self._subscribed:
                logger.debug("market_data_subscribe_ignored_already_subscribed symbol=%s", symbol)
                return
            self._subscribed.add(symbol)
        logger.info("market_data_subscribe_started symbol=%s", symbol)
        try:
            self._seed_baseline_history(symbol)
            self.ws_feed.subscribe(symbol)
            logger.info("market_data_subscribe_complete symbol=%s", symbol)
        except Exception:
            with self._lock:
                self._subscribed.discard(symbol)
            logger.exception("market_data_subscribe_failed symbol=%s", symbol)
            raise

    def unsubscribe(self, symbol: str) -> None:
        with self._lock:
            was_subscribed = symbol in self._subscribed
            self._subscribed.discard(symbol)
            self._degraded.discard(symbol)
            self._last_health.pop(symbol, None)
        self.ws_feed.unsubscribe(symbol)
        self.rest_fallback.disengage(symbol)
        if was_subscribed:
            logger.info("market_data_unsubscribed symbol=%s", symbol)

    def get_live_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        return self.candle_builder.get_live_candle(symbol, timeframe)

    def get_historical_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Explicit broker-history read. Not permitted for Trading Panel
        rendering or chart polling. Use get_chart_candles() for chart data."""
        end_ms = self._now_ms()
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        candles = self.historical_loader.fetch_range(symbol, timeframe, start_ms, end_ms)
        logger.debug(
            "market_data_historical_fetch symbol=%s timeframe=%s days=%d candles=%d",
            symbol, timeframe, days, len(candles),
        )
        return candles

    def get_chart_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Return local-only chart candles, oldest to newest. Merges
        CandleStoreWorker (persistent SQLite) with CandleBuilderWorker's
        in-memory RAM series - RAM wins on any timestamp collision (it
        always has the current forming candle). Deliberately continues to
        include the RAM baseline window even after a deep-history Delete -
        see module docstring."""
        if days <= 0:
            return []

        cutoff_ms = self._now_ms() - days * 24 * 60 * 60 * 1000
        now_ms = self._now_ms()

        merged: Dict[int, Candle] = {}

        persisted = self.candle_store.get_candles(symbol, timeframe, cutoff_ms, now_ms)
        for candle in persisted:
            merged[candle.open_time] = candle

        series = self.candle_builder.get_series(symbol, timeframe)
        for candle in series:
            if candle.open_time >= cutoff_ms:
                merged[candle.open_time] = candle

        result = [merged[open_time] for open_time in sorted(merged)]

        logger.debug(
            "market_data_chart_local_read symbol=%s timeframe=%s requested_days=%d persisted=%d ram=%d merged=%d",
            symbol, timeframe, days, len(persisted), len(series), len(result),
        )
        return result

    def get_recent_window(
        self, symbol: str, timeframe: str, end_ms: Optional[int] = None,
        visible_days: int = 1, older_buffer_days: int = 2,
    ) -> dict:
        if end_ms is None:
            end_ms = self._now_ms()
        return self.candle_store.get_recent_window(
            symbol, timeframe, int(end_ms), visible_days=visible_days, older_buffer_days=older_buffer_days,
        )

    def get_local_coverage(self, symbol: str, timeframe: str, requested_days: Optional[int] = None) -> dict:
        coverage = self.candle_store.get_local_coverage(symbol, timeframe, requested_days, self._now_ms())
        return coverage.to_dict()

    def sqlite_coverage_payload(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> dict:
        """Real-time coverage callback wired into DeepHistoryDownloaderWorker.
        Computes required/present/missing candle counts directly from
        physical SQLite rows for the exact window the downloader is
        currently working on - this is what makes the progress bar and
        ETA in the UI genuinely truthful instead of a guess."""
        requested_days = max(1, int((end_ms - start_ms) / DAY_MS))
        return self.candle_store.get_local_coverage(symbol, timeframe, requested_days, end_ms).to_dict()

    def get_chart_coverage_days(self, symbol: str, timeframe: str) -> float:
        return self.candle_store.get_chart_coverage_days(symbol, timeframe)

    def get_health(self) -> Dict[str, str]:
        report: Dict[str, str] = {}
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            if self.ws_feed.is_healthy(symbol):
                health = "OK"
            elif self.rest_fallback.is_engaged(symbol):
                health = "DEGRADED"
            else:
                health = "DOWN"
            report[symbol] = health
            self._log_health_transition(symbol, health)
        return report

    # ================= deep history / ceiling interface =================

    def start_deep_history(self, symbol: str, timeframe: str, target_days: Optional[int] = None) -> None:
        logger.info("deep_history_started symbol=%s timeframe=%s target_days=%s", symbol, timeframe, target_days)
        self.deep_history_downloader.start_download(symbol, timeframe, target_days)

    def cancel_deep_history(self, symbol: str, timeframe: str) -> None:
        logger.info("deep_history_cancel_requested symbol=%s timeframe=%s", symbol, timeframe)
        self.deep_history_downloader.cancel_download(symbol, timeframe)

    def get_deep_history_progress(self, symbol: str, timeframe: str) -> dict:
        """Full real-time download progress, sourced directly from
        DeepHistoryDownloaderWorker.get_status() (percent, present/
        required/missing candle counts, eta_seconds, broker ceiling flag)
        plus physical SQLite coverage. This is the single source of truth
        the Trading Panel and Deep Historical Data card must bind to -
        there is no other progress signal anywhere else in the app."""
        status = self.deep_history_downloader.get_status(symbol, timeframe)
        coverage = self.candle_store.get_local_coverage(symbol, timeframe)
        return {
            "state": status["state"],
            "error": status["error"],
            "percent": status["percent"],
            "present_candles": status["present_candles"],
            "required_candles": status["required_candles"],
            "missing_candles": status["missing_candles"],
            "eta_seconds": status["eta_seconds"],
            "broker_ceiling_reached": status["broker_ceiling_reached"],
            "covered_days": coverage.contiguous_days,
            "is_complete": status["state"] == "complete",
        }

    def delete_deep_history(self, symbol: str, timeframe: str) -> None:
        logger.warning("deep_history_delete_requested symbol=%s timeframe=%s", symbol, timeframe)
        self.history_manifest.delete_symbol_manifest(symbol)
        self.candle_store.delete_symbol_timeframe(symbol, timeframe)
        self.deep_history_downloader.reset_status(symbol, timeframe)

    def start_ceiling_probe(self, symbol: str, timeframe: str) -> None:
        logger.info("history_ceiling_probe_started symbol=%s timeframe=%s", symbol, timeframe)
        self.depth_prober.start_probe(symbol, timeframe)

    def get_ceiling_days(self, symbol: str, timeframe: str):
        return self.depth_prober.get_ceiling_days(symbol, timeframe)

    # ================= internal wiring =================

    def _seed_baseline_history(self, symbol: str) -> None:
        started = time.monotonic()
        logger.info("baseline_seed_started symbol=%s timeframes=%s", symbol, TRADING_TFS)
        baseline = self.historical_loader.backfill_baseline(symbol)
        counts: Dict[str, int] = {}
        for timeframe, candles in baseline.items():
            self.candle_builder.seed_historical(symbol, timeframe, candles)
            counts[timeframe] = len(candles)
        logger.info(
            "baseline_seed_complete symbol=%s counts=%s duration_s=%.3f",
            symbol, counts, time.monotonic() - started,
        )

    def _handle_ws_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_ws_payload(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)
        else:
            logger.warning(
                "ws_price_bearing_delta_rejected_by_normalizer symbol=%s keys=%s",
                symbol, sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
            )

    def _handle_rest_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_rest_ticker(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)
        else:
            logger.debug("rest_tick_rejected_by_normalizer symbol=%s", symbol)

    def _handle_ws_drop(self, symbol: str) -> None:
        with self._lock:
            already_degraded = symbol in self._degraded
            self._degraded.add(symbol)
        if not already_degraded:
            logger.warning("ws_drop_rest_fallback_engaging symbol=%s", symbol)
            self.rest_fallback.engage(symbol)

    def _handle_ws_restore(self, symbol: str) -> None:
        with self._lock:
            was_degraded = symbol in self._degraded
            self._degraded.discard(symbol)
        self.rest_fallback.disengage(symbol)
        if was_degraded:
            logger.info("ws_restored_rest_fallback_disengaged symbol=%s", symbol)

    def _handle_deep_history_chunk(self, symbol: str, timeframe: str, candles: list) -> None:
        saved = self.candle_store.save_candles(symbol, timeframe, candles)
        logger.debug(
            "deep_history_chunk_persisted symbol=%s timeframe=%s rows=%d",
            symbol, timeframe, saved,
        )

    def _publish_candle_closed(self, candle: Candle) -> None:
        try:
            self.candle_store.save_candles(candle.symbol, candle.timeframe, [candle])
        except Exception:
            logger.exception(
                "candle_close_persist_failed symbol=%s timeframe=%s open_time=%d",
                candle.symbol, candle.timeframe, candle.open_time,
            )
        logger.debug(
            "candle_closed symbol=%s timeframe=%s open_time=%d close=%s",
            candle.symbol, candle.timeframe, candle.open_time, candle.close,
        )

    def _log_health_transition(self, symbol: str, health: str) -> None:
        with self._lock:
            previous = self._last_health.get(symbol)
            self._last_health[symbol] = health
        if previous != health:
            level = logging.INFO if health == "OK" else logging.WARNING
            logger.log(
                level, "market_data_health_transition symbol=%s previous=%s current=%s",
                symbol, previous or "UNSET", health,
            )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)
